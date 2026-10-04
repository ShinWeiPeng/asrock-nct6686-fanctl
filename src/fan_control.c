/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifdef __KERNEL__
#include <linux/errno.h>
#else
#include <errno.h>
#endif
#include "fan_control.h"

int fan_control_can_write(const struct fan_control *ctl, unsigned int channel)
{
	return ctl && ctl->authorized && ctl->channel < 8 && channel == ctl->channel &&
	       ctl->io.read && ctl->io.write && ctl->io.sleep_ms;
}
unsigned int fan_control_map_pwm(const struct fan_control *ctl, unsigned int channel,
				 unsigned int raw)
{
	return fan_control_can_write(ctl, channel) && ctl->invert ? 255 - raw : raw;
}
static int wait_mode(struct fan_control *ctl, unsigned int expected)
{
	unsigned int i;
	int actual;
	for (i = 0; i < FAN_POLL_COUNT; i++) {
		ctl->io.sleep_ms(ctl->io.context, FAN_POLL_MS);
		actual = ctl->io.read(ctl->io.context, FAN_MODE_REG);
		if (actual < 0)
			return actual;
		if ((unsigned int)actual == expected)
			return 0;
	}
	return -ETIMEDOUT;
}
int fan_control_set_mode(struct fan_control *ctl, unsigned int channel, unsigned int mode)
{
	int current, result;
	unsigned int next;
	if (channel >= 8 || (mode != 1 && mode != 2))
		return -EINVAL;
	if (!fan_control_can_write(ctl, channel))
		return -EPERM;
	if (mode == 1) {
		current = ctl->io.read(ctl->io.context, FAN_PWM_READ(channel));
		if (current < 0)
			return current;
		/* Freeze the current raw output, including a verified inverse mapping. */
		return fan_control_set_pwm(ctl, channel,
					   fan_control_map_pwm(ctl, channel, current));
	}
	current = ctl->io.read(ctl->io.context, FAN_MODE_REG);
	if (current < 0)
		return current;
	next = (unsigned int)current & ~(1U << channel);
	result = ctl->io.write(ctl->io.context, FAN_MODE_REG, (unsigned char)next);
	if (result)
		return result;
	result = wait_mode(ctl, next);
	if (!result)
		ctl->touched = 0;
	return result;
}
int fan_control_release(struct fan_control *ctl)
{
	if (!ctl || !ctl->touched)
		return 0;
	return fan_control_set_mode(ctl, ctl->channel, 2);
}
int fan_control_set_pwm(struct fan_control *ctl, unsigned int channel, unsigned int value)
{
	int mode, busy, actual, result;
	unsigned int raw, expected_mode, i;
	if (channel >= 8 || value > 255)
		return -EINVAL;
	if (!fan_control_can_write(ctl, channel))
		return -EPERM;
	busy = ctl->io.read(ctl->io.context, FAN_COMMAND_REG);
	if (busy < 0)
		return busy;
	if (busy & 0x80)
		return -EBUSY;
	mode = ctl->io.read(ctl->io.context, FAN_MODE_REG);
	if (mode < 0)
		return mode;
	raw = fan_control_map_pwm(ctl, channel, value);
	expected_mode = (unsigned int)mode | (1U << channel);
	/* Keep cleanup required even when a hardware write's outcome is uncertain. */
	ctl->touched = 1;
	result = ctl->io.write(ctl->io.context, FAN_MODE_REG, (unsigned char)expected_mode);
	if (result)
		goto restore;
	result = ctl->io.write(ctl->io.context, FAN_COMMAND_REG, 0x80);
	if (result)
		goto finish_command;
	ctl->io.sleep_ms(ctl->io.context, FAN_POLL_MS);
	result = ctl->io.write(ctl->io.context, FAN_PWM_WRITE(channel), (unsigned char)raw);
finish_command:
	{
		int done = ctl->io.write(ctl->io.context, FAN_COMMAND_REG, 0);
		if (!result)
			result = done;
	}
	if (result)
		goto restore;
	for (i = 0; i < FAN_POLL_COUNT; i++) {
		ctl->io.sleep_ms(ctl->io.context, FAN_POLL_MS);
		actual = ctl->io.read(ctl->io.context, FAN_PWM_READ(channel));
		mode = ctl->io.read(ctl->io.context, FAN_MODE_REG);
		if (actual < 0 || mode < 0) {
			result = actual < 0 ? actual : mode;
			goto restore;
		}
		if ((unsigned int)actual == raw && (unsigned int)mode == expected_mode)
			return 0;
	}
	result = -ETIMEDOUT;
restore:
	/* Best effort: the adapter reports an error and retained touched state. */
	(void)fan_control_release(ctl);
	return result;
}

int fan_control_recover(struct fan_control *ctl)
{
	int restore = 0, handoff;
	if (!ctl)
		return -EINVAL;
	if (ctl->restore_pending) {
		if (!fan_control_can_write(ctl, 3) || ctl->invert)
			return -EPERM;
		restore = fan_control_set_pwm(ctl, 3, 165);
		if (!restore)
			ctl->restore_pending = 0;
	}
	handoff = fan_control_release(ctl);
	return restore ? restore : handoff;
}
int fan_control_identify_once(struct fan_control *ctl)
{
	int mode, raw, busy, result, recovery;
	unsigned int expected_mode;
	if (!fan_control_can_write(ctl, 3) || ctl->invert || ctl->touched || ctl->restore_pending)
		return -EPERM;
	mode = ctl->io.read(ctl->io.context, FAN_MODE_REG);
	if (mode < 0)
		return mode;
	if (mode & (1U << 3))
		return -EBUSY;
	expected_mode = (unsigned int)mode | (1U << 3);
	raw = ctl->io.read(ctl->io.context, FAN_PWM_READ(3));
	if (raw < 0)
		return raw;
	if (raw != 165)
		return -EINVAL;
	busy = ctl->io.read(ctl->io.context, FAN_COMMAND_REG);
	if (busy < 0)
		return busy;
	if (busy & 0x80)
		return -EBUSY;
	ctl->restore_pending = 1;
	result = fan_control_set_pwm(ctl, 3, 120);
	if (result == -EBUSY && !ctl->touched) {
		ctl->restore_pending = 0;
		return result;
	}
	if (!result) {
		ctl->io.sleep_ms(ctl->io.context, 3000);
		raw = ctl->io.read(ctl->io.context, FAN_PWM_READ(3));
		mode = ctl->io.read(ctl->io.context, FAN_MODE_REG);
		if (raw < 0 || mode < 0)
			result = raw < 0 ? raw : mode;
		else if (raw != 120 || (unsigned int)mode != expected_mode)
			result = -EIO;
	}
	/* Recover the baseline even when the failed pulse already released BIOS. */
	recovery = fan_control_recover(ctl);
	return result ? result : recovery;
}
