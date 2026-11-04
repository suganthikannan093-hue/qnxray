/*
 * qnxray-agent: target-side collector for QNX SDP 8.0 (built with qcc -Vgcc_ntox86_64).
 * Walks /proc/<pid>/ctl and uses devctl() DCMD_PROC_INFO / DCMD_PROC_TIDSTATUS
 * (<sys/procfs.h>, <sys/debug.h>). Emits NDJSON snapshots on stdout in the same schema
 * as the host CLI's Snapshot model: {"source","timestamp","processes":[{pid,name,threads:[...]}]}.
 * Usage: qnxray-agent [interval_sec] [count]   (count 0 = forever). Run as root to see all pids.
 * TODO: serve the same data from a resource manager at /dev/qnxray.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <devctl.h>
#include <sys/procfs.h>
#include <sys/states.h>

static const char *state_name(unsigned s) {
    static const char *n[] = {"DEAD","RUNNING","READY","STOPPED","SEND","RECEIVE","REPLY",
        "MQ_SEND","MQ_RECEIVE","WAITPAGE","SIGSUSPEND","SIGWAITINFO","NANOSLEEP","MUTEX",
        "CONDVAR","JOIN","INTR","SEM","WAITCTX","RWLOCK_READ","RWLOCK_WRITE","BARRIER","PIPE",
        "???","CREATE","DESTROY","MUON_MUTEX","TRACEBUFFER","INTR_ATTACH_EV","TIMER_DELEGATE","SEND_NOTIFY"};
    return s < sizeof n / sizeof *n ? n[s] : "???";
}
static char policy_char(int p) {
    switch (p) { case SCHED_FIFO: return 'f'; case SCHED_RR: return 'r';
                 case SCHED_SPORADIC: return 's'; default: return 'o'; }
}
static void json_str(const char *s) {
    putchar('"');
    for (; *s; s++) { if (*s == '"' || *s == '\\') putchar('\\'); if ((unsigned char)*s >= 0x20) putchar(*s); }
    putchar('"');
}
static int dump_process(int pid, int first) {
    char path[64], name[256] = "?";
    snprintf(path, sizeof path, "/proc/%d/exefile", pid);
    FILE *f = fopen(path, "r");
    if (f) { if (!fgets(name, sizeof name, f)) strcpy(name, "?"); fclose(f); name[strcspn(name, "\n")] = 0; }
    snprintf(path, sizeof path, "/proc/%d/ctl", pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return 0;
    procfs_info info;
    if (devctl(fd, DCMD_PROC_INFO, &info, sizeof info, NULL) != EOK) { close(fd); return 0; }
    printf("%s{\"pid\":%d,\"name\":", first ? "" : ",", pid); json_str(name);
    printf(",\"threads\":[");
    procfs_status st; int tf = 1;
    memset(&st, 0, sizeof st);
    for (st.tid = 1; ; st.tid++) {
        if (devctl(fd, DCMD_PROC_TIDSTATUS, &st, sizeof st, NULL) != EOK) break;
        char blk[32] = "";
        if (st.state == STATE_SEND || st.state == STATE_REPLY)
            snprintf(blk, sizeof blk, "%d", st.blocked.connect.pid);
        else if (st.state == STATE_RECEIVE)
            snprintf(blk, sizeof blk, "%d", st.blocked.channel.chid);
        printf("%s{\"tid\":%d,\"name\":", tf ? "" : ",", (int)st.tid); json_str(name);
        printf(",\"priority\":%u,\"policy\":\"%c\",\"state\":\"%s\",\"blocked_on\":%s%s%s,\"cpu\":%u}",
               st.priority, policy_char(st.policy), state_name(st.state),
               blk[0] ? "\"" : "", blk[0] ? blk : "null", blk[0] ? "\"" : "", st.last_cpu);
        tf = 0;
    }
    printf("]}");
    close(fd);
    return 1;
}
int main(int argc, char **argv) {
    int interval = argc > 1 ? atoi(argv[1]) : 1;
    int count = argc > 2 ? atoi(argv[2]) : 0;
    for (int n = 0; count == 0 || n < count; n++) {
        DIR *d = opendir("/proc");
        struct dirent *e; int first = 1;
        printf("{\"source\":\"agent\",\"timestamp\":%ld,\"processes\":[", (long)time(NULL));
        while (d && (e = readdir(d))) {
            int pid = atoi(e->d_name);
            if (pid <= 0) continue;
            if (dump_process(pid, first)) first = 0;
        }
        printf("]}\n"); fflush(stdout);
        if (d) closedir(d);
        if (count == 0 || n + 1 < count) sleep(interval);
    }
    return 0;
}
