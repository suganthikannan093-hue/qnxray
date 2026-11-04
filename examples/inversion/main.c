/*
 * Priority-inversion demo for QNX 8.0.
 * Three processes pinned to CPU 0:
 *   server  prio 10 (FIFO) - owns a channel created with _NTO_CHF_FIXED_PRIORITY, so it does
 *                            NOT inherit its clients' priority (inheritance disabled on purpose)
 *   hog     prio 20 (FIFO) - CPU-bound medium-priority work that starves the server
 *   client  prio 30 (FIFO) - MsgSend()s to the server and stays REPLY-blocked on a prio-10 server
 * => the prio-30 client is effectively running at prio 10 and loses to the prio-20 hog.
 * Usage (as root): inversion [seconds=20] [--inherit]
 *   --inherit: create the channel without _NTO_CHF_FIXED_PRIORITY (the fix).
 * Fix: drop _NTO_CHF_FIXED_PRIORITY (QNX's default priority inheritance) and the inversion goes away.
 */
#include <errno.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <sys/neutrino.h>
#include <sys/wait.h>

static void setup(int prio, const char *who) {
    ThreadCtl(_NTO_TCTL_RUNMASK, (void *)(uintptr_t)1);            /* pin to CPU 0 */
    struct sched_param sp = { .sched_priority = prio };
    if (sched_setscheduler(0, SCHED_FIFO, &sp) == -1)
        fprintf(stderr, "%s: sched_setscheduler: %s (run as root)\n", who, strerror(errno));
}
static double now(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec / 1e9; }
static void spin(double s) { double e = now() + s; volatile unsigned long x = 0; while (now() < e) x++; }

int main(int argc, char **argv) {
    int secs = argc > 1 ? atoi(argv[1]) : 20;
    int inherit = argc > 2 && strcmp(argv[2], "--inherit") == 0;
    /* The bug: _NTO_CHF_FIXED_PRIORITY turns off QNX's client-driven priority inheritance. */
    int chid = ChannelCreate(inherit ? 0 : _NTO_CHF_FIXED_PRIORITY);
    pid_t server = getpid();
    pid_t hog = fork();
    if (hog == 0) {                      /* medium: wait for the server to be busy, then hog CPU 0 */
        setup(20, "hog"); usleep(300000); spin(secs); _exit(0);
    }
    pid_t client = fork();
    if (client == 0) {                   /* high: one request, blocks until server replies */
        setup(30, "client"); usleep(100000);
        int coid = ConnectAttach(0, server, chid, _NTO_SIDE_CHANNEL, 0);
        char req[] = "work", rep[16];
        double t0 = now();
        MsgSend(coid, req, sizeof req, rep, sizeof rep);
        double dt = now() - t0;
        printf("client(prio 30): reply after %.2fs (expected 0.5s)%s\n", dt,
               dt > 0.8 ? " -> priority inversion" : " -> OK, server inherited prio 30");
        fflush(stdout);
        _exit(0);
    }
    setup(10, "server");
    printf("inversion demo: server=%d hog=%d client=%d (pidin -p %d)\n", server, hog, client, client);
    fflush(stdout);
    char msg[16];
    int rcvid = MsgReceive(chid, msg, sizeof msg, NULL);
    spin(0.5);                           /* 0.5 s of CPU work; preempted by the hog unless it inherited prio 30 */
    MsgReply(rcvid, 0, "done", 5);
    waitpid(client, NULL, 0);
    kill(hog, SIGTERM); waitpid(hog, NULL, 0);
    return 0;
}
