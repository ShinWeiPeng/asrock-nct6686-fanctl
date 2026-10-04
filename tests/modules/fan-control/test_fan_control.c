/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "fan_control.h"

struct fake_ec {
	unsigned char regs[0x1000];
	unsigned int writes, sleeps, foreign_pwm_writes;
	unsigned int selected, holds, pwm_count;
	unsigned char pwm_history[16];
	int drop_pwm, drop_mode, fail_write;
	unsigned int fail_at, reads, fail_read_at, change_hold;
};
static int read_ec(void *context, unsigned int reg)
{
	struct fake_ec *ec = context;
	assert(reg < sizeof(ec->regs));
	ec->reads++;
	if (ec->reads == ec->fail_read_at)
		return -EIO;
	return ec->regs[reg];
}
static int write_ec(void *context, unsigned int reg, unsigned char value)
{
	struct fake_ec *ec = context;
	ec->writes++;
	if (ec->fail_write || ec->writes == ec->fail_at)
		return -EIO;
	if (reg >= 0xa28 && reg <= 0xa2f) {
		if (reg == FAN_PWM_WRITE(ec->selected)) {
			assert(ec->pwm_count < sizeof(ec->pwm_history));
			ec->pwm_history[ec->pwm_count++] = value;
		}
		if (reg != FAN_PWM_WRITE(ec->selected))
			ec->foreign_pwm_writes++;
		if (!ec->drop_pwm)
			ec->regs[0x160 + reg - 0xa28] = value;
	}
	if (reg != FAN_MODE_REG || !ec->drop_mode)
		ec->regs[reg] = value;
	return 0;
}
static void wait_ec(void *context, unsigned int ms)
{
	struct fake_ec *ec = context;
	if (ms == 3000) {
		assert(ec->regs[FAN_PWM_READ(3)] == 120);
		ec->holds++;
		if (ec->change_hold == 1)
			ec->regs[FAN_PWM_READ(3)] = 159;
		if (ec->change_hold == 2)
			ec->regs[FAN_MODE_REG] &= ~(1U << 3);
	} else {
		assert(ms == FAN_POLL_MS);
	}
	ec->sleeps++;
}
static struct fan_control setup(struct fake_ec *ec, unsigned int channel)
{
	struct fan_control ctl = {
	    .io = {ec, read_ec, write_ec, wait_ec},
	    .channel = channel,
	    .authorized = 1,
	};
	memset(ec, 0, sizeof(*ec));
	ec->selected = channel;
	return ctl;
}
static void readonly_is_effect_free(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	ctl.authorized = 0;
	assert(fan_control_set_pwm(&ctl, 3, 165) == -EPERM);
	assert(fan_control_set_mode(&ctl, 3, 1) == -EPERM);
	assert(fan_control_release(&ctl) == 0);
	assert(ec.writes == 0);
}
static void only_verified_channel_changes(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	/* Literal hardware fixture: other channels already in manual mode. */
	ec.regs[FAN_MODE_REG] = 0xa5;
	ec.regs[FAN_PWM_READ(0)] = 255;
	ec.regs[FAN_PWM_READ(1)] = 210;
	ec.regs[FAN_PWM_READ(3)] = 165;
	assert(fan_control_set_pwm(&ctl, 3, 160) == 0);
	assert(ec.regs[FAN_MODE_REG] == 0xad);
	assert(ec.regs[FAN_PWM_READ(3)] == 160);
	assert(ec.regs[FAN_PWM_READ(0)] == 255);
	assert(ec.regs[FAN_PWM_READ(1)] == 210);
	assert(ec.foreign_pwm_writes == 0);
	assert(ctl.touched);
	assert(fan_control_set_pwm(&ctl, 0, 128) == -EPERM);
	assert(fan_control_set_mode(&ctl, 0, 2) == -EPERM);
	assert(fan_control_set_mode(&ctl, 3, 2) == 0);
	assert(ec.regs[FAN_MODE_REG] == 0xa5);
	assert(!ctl.touched);
}

static void all_channel_masks_are_isolated(void)
{
	const unsigned char bits[] = {1, 2, 4, 8, 16, 32, 64, 128};
	unsigned int channel;
	for (channel = 0; channel < 8; channel++) {
		struct fake_ec ec;
		struct fan_control ctl = setup(&ec, channel);
		assert(fan_control_set_pwm(&ctl, channel, 200) == 0);
		assert(ec.regs[FAN_MODE_REG] == bits[channel]);
		assert(ec.foreign_pwm_writes == 0);
		assert(fan_control_release(&ctl) == 0);
		assert(ec.regs[FAN_MODE_REG] == 0);
	}
}
static void failure_is_not_reported_as_success(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xa5;
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.drop_pwm = 1;
	assert(fan_control_set_pwm(&ctl, 3, 160) == -ETIMEDOUT);
	assert(ec.regs[FAN_MODE_REG] == 0xa5);
	assert(ec.regs[FAN_COMMAND_REG] == 0);
	assert(ec.sleeps <= 22);
	assert(!ctl.touched);
	ctl = setup(&ec, 3);
	ec.drop_mode = 1;
	assert(fan_control_set_pwm(&ctl, 3, 160) == -ETIMEDOUT);
	ctl = setup(&ec, 3);
	ec.fail_write = 1;
	assert(fan_control_set_pwm(&ctl, 3, 160) == -EIO);
	assert(ctl.touched);
	ec.fail_write = 0;
	assert(fan_control_release(&ctl) == 0);
	assert(!ctl.touched);
}
static void invalid_and_busy_requests_have_no_effects(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	assert(fan_control_set_pwm(&ctl, 3, 256) == -EINVAL);
	assert(fan_control_set_pwm(&ctl, 8, 128) == -EINVAL);
	assert(fan_control_set_mode(&ctl, 3, 0) == -EINVAL);
	assert(fan_control_set_mode(&ctl, 3, 99) == -EINVAL);
	ec.regs[FAN_COMMAND_REG] = 0x80;
	assert(fan_control_set_pwm(&ctl, 3, 160) == -EBUSY);
	assert(ec.writes == 0);
}
static void polarity_mapping_requires_verified_control(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	ctl.invert = 1;
	assert(fan_control_set_pwm(&ctl, 3, 200) == 0);
	assert(ec.regs[FAN_PWM_READ(3)] == 55);
	assert(fan_control_map_pwm(&ctl, 3, 55) == 200);
	assert(fan_control_map_pwm(&ctl, 0, 55) == 55);
	assert(fan_control_set_mode(&ctl, 3, 1) == 0);
	assert(ec.regs[FAN_PWM_READ(3)] == 55);
	assert(fan_control_release(&ctl) == 0);
	ctl.authorized = 0;
	assert(fan_control_map_pwm(&ctl, 3, 55) == 55);
}

static void one_identification_is_bounded_and_restores_baseline(void)
{
	struct fake_ec ec;
	struct fan_control ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_PWM_READ(0)] = 255;
	ec.regs[FAN_PWM_READ(1)] = 255;
	ec.regs[FAN_PWM_READ(3)] = 165;
	assert(fan_control_identify_once(&ctl) == 0);
	assert(ec.holds == 1);
	assert(ec.pwm_count == 2);
	assert(ec.pwm_history[0] == 120);
	assert(ec.pwm_history[1] == 165);
	assert(ec.regs[FAN_PWM_READ(3)] == 165);
	assert(ec.regs[FAN_PWM_READ(0)] == 255);
	assert(ec.regs[FAN_PWM_READ(1)] == 255);
	assert(ec.regs[FAN_MODE_REG] == 0xf4);
	assert(!ctl.touched);
	assert(!ctl.restore_pending);
	assert(ec.foreign_pwm_writes == 0);
	assert(ec.sleeps <= 64);
	ctl = setup(&ec, 3);
	ec.regs[FAN_PWM_READ(3)] = 164;
	assert(fan_control_identify_once(&ctl) == -EINVAL);
	assert(ec.writes == 0);
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.regs[FAN_MODE_REG] = 0xfc;
	assert(fan_control_identify_once(&ctl) == -EBUSY);
	assert(ec.writes == 0);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_COMMAND_REG] = 0x80;
	assert(fan_control_identify_once(&ctl) == -EBUSY);
	assert(ec.writes == 0);
	ec.regs[FAN_COMMAND_REG] = 0;
	ctl.invert = 1;
	assert(fan_control_identify_once(&ctl) == -EPERM);
	ctl.invert = 0;
	ctl.authorized = 0;
	assert(fan_control_identify_once(&ctl) == -EPERM);
	assert(ec.writes == 0);
	ctl = setup(&ec, 2);
	assert(fan_control_identify_once(&ctl) == -EPERM);
	assert(ec.writes == 0);
	ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.drop_pwm = 1;
	assert(fan_control_identify_once(&ctl) == -ETIMEDOUT);
	assert(ec.holds == 0);
	assert(ec.regs[FAN_PWM_READ(3)] == 165);
	assert(ec.regs[FAN_MODE_REG] == 0xf4);
	assert(ec.foreign_pwm_writes == 0);
	ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.fail_write = 1;
	assert(fan_control_identify_once(&ctl) == -EIO);
	assert(ctl.touched);
	ec.fail_write = 0;
	assert(fan_control_release(&ctl) == 0);

	ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.fail_at = 5; /* first baseline-restore mode write, after successful hold */
	assert(fan_control_identify_once(&ctl) == -EIO);
	assert(ec.holds == 1);
	assert(ctl.restore_pending);
	assert(!ctl.touched);
	assert(ec.regs[FAN_PWM_READ(3)] == 120);
	assert(ec.regs[FAN_MODE_REG] == 0xf4);
	assert(fan_control_recover(&ctl) == 0);
	assert(ec.regs[FAN_PWM_READ(3)] == 165);
	assert(ec.regs[FAN_MODE_REG] == 0xf4);
	assert(!ctl.restore_pending && !ctl.touched);
}

static void identification_readback_and_handoff_failures_are_visible(void)
{
	struct fake_ec ec;
	struct fan_control ctl;
	unsigned int i;
	for (i = 1; i <= 3; i++) {
		ctl = setup(&ec, 3);
		ec.regs[FAN_MODE_REG] = 0xf4;
		ec.regs[FAN_PWM_READ(3)] = 165;
		ec.fail_read_at = i;
		assert(fan_control_identify_once(&ctl) == -EIO);
		assert(!ec.writes && !ec.holds && !ctl.restore_pending);
	}
	for (i = 8; i <= 9; i++) {
		ctl = setup(&ec, 3);
		ec.regs[FAN_MODE_REG] = 0xf4;
		ec.regs[FAN_PWM_READ(3)] = 165;
		ec.fail_read_at = i;
		assert(fan_control_identify_once(&ctl) == -EIO);
		assert(ec.holds == 1 && !ctl.restore_pending && !ctl.touched);
		assert(ec.regs[FAN_PWM_READ(3)] == 165);
		assert(ec.regs[FAN_MODE_REG] == 0xf4);
		assert(!ec.foreign_pwm_writes);
	}
	for (i = 1; i <= 2; i++) {
		ctl = setup(&ec, 3);
		ec.regs[FAN_MODE_REG] = 0xf4;
		ec.regs[FAN_PWM_READ(3)] = 165;
		ec.change_hold = i;
		assert(fan_control_identify_once(&ctl) == -EIO);
		assert(ec.holds == 1 && !ctl.restore_pending && !ctl.touched);
		assert(ec.regs[FAN_PWM_READ(3)] == 165);
		assert(ec.regs[FAN_MODE_REG] == 0xf4);
		assert(!ec.foreign_pwm_writes);
	}
	ctl = setup(&ec, 3);
	ec.regs[FAN_MODE_REG] = 0xf4;
	ec.regs[FAN_PWM_READ(3)] = 165;
	ec.fail_at = 9; /* final BIOS handoff only */
	assert(fan_control_identify_once(&ctl) == -EIO);
	assert(!ctl.restore_pending && ctl.touched);
	assert(ec.regs[FAN_PWM_READ(3)] == 165);
	assert(ec.regs[FAN_MODE_REG] == 0xfc);
	assert(fan_control_recover(&ctl) == 0);
	assert(!ctl.touched && ec.holds == 1);
	assert(ec.regs[FAN_MODE_REG] == 0xf4);
	assert(!ec.foreign_pwm_writes);
}

int main(void)
{
	readonly_is_effect_free();
	only_verified_channel_changes();
	all_channel_masks_are_isolated();
	failure_is_not_reported_as_success();
	invalid_and_busy_requests_have_no_effects();
	polarity_mapping_requires_verified_control();
	one_identification_is_bounded_and_restores_baseline();
	identification_readback_and_handoff_failures_are_visible();
	puts("PASS: 8 control scenarios, all 8 channel masks, timeout, busy, invalid values, "
	     "inverse PWM, one-shot identification and BIOS cleanup");
	return 0;
}
