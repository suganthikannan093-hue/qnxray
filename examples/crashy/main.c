/* Deliberately crashing demo app for the AI explainer (build with qcc -Vgcc_ntox86_64 -g). */
#include <stdio.h>
#include <stddef.h>
struct sensor { int value; };
static int read_sensor(struct sensor *s) { return s->value; }   /* NULL deref */
int main(void) { struct sensor *s = NULL; printf("%d\n", read_sensor(s)); return 0; }
