/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef ASROCK_FAN_CONTROL_H
#define ASROCK_FAN_CONTROL_H

#define FAN_MODE_REG 0xa00
#define FAN_COMMAND_REG 0xa01
#define FAN_PWM_READ(n) (0x160 + (n))
#define FAN_PWM_WRITE(n) (0xa28 + (n))
#define FAN_POLL_COUNT 20
#define FAN_POLL_MS 50

/* All callbacks run with the adapter's EC mutex held. */
struct fan_io {
	void *context;
	int (*read)(void *context, unsigned int reg);
	int (*write)(void *context, unsigned int reg, unsigned char value);
	void (*sleep_ms)(void *context, unsigned int ms);
};

struct fan_control {
	struct fan_io io;
	unsigned int channel; /* zero based, selected by verified physical mapping */
	unsigned int authorized;
	unsigned int invert;
	unsigned int touched;
	unsigned int restore_pending; /* candidate identification baseline recovery */
};

int fan_control_can_write(const struct fan_control *ctl, unsigned int channel);
int fan_control_set_pwm(struct fan_control *ctl, unsigned int channel, unsigned int value);
int fan_control_set_mode(struct fan_control *ctl, unsigned int channel, unsigned int mode);
int fan_control_release(struct fan_control *ctl);
unsigned int fan_control_map_pwm(const struct fan_control *ctl, unsigned int channel,
				 unsigned int raw);
int fan_control_recover(struct fan_control *ctl);
int fan_control_identify_once(struct fan_control *ctl);
#endif
