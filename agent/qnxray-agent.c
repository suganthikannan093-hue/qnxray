/*
 * qnxray-agent: target-side collector for QNX 8.0 (NOT YET COMPILED - needs qcc from QNX SDP 8.0).
 * Walks /proc/<pid>/ctl and uses devctl() with DCMD_PROC_INFO and DCMD_PROC_TIDSTATUS
 * (QNX 8.0 Programmer's Guide, "Controlling processes via the /proc filesystem").
 * Emits one NDJSON snapshot per interval on stdout (later: served via a resource manager
 * at /dev/qnxray so host tools can read it - targets the "Best use of QNX tech" prize).
 * Struct field names below must be verified against <sys/procfs.h> / <sys/debug.h> in SDP 8.0.
 */
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <devctl.h>
#include <sys/procfs.h>

static void dump_process(int pid) {
    char path[64];
    snprintf(path, sizeof path, "/proc/%d/ctl", pid);
    int fd = open(path, O_RDONLY);
    if (fd < 0) return;
    procfs_info info;
    if (devctl(fd, DCMD_PROC_INFO, &info, sizeof info, NULL) == EOK) {
        printf("{\"pid\":%d,\"num_threads\":%u,\"threads\":[", pid, (unsigned)info.num_threads);
        procfs_status st;
        int first = 1;
        for (st.tid = 1; ; st.tid++) {
            if (devctl(fd, DCMD_PROC_TIDSTATUS, &st, sizeof st, NULL) != EOK) break;
            printf("%s{\"tid\":%d,\"prio\":%d,\"policy\":%d,\"state\":%d}",
                   first ? "" : ",", st.tid, st.priority, st.policy, st.state);
            first = 0;
        }
        printf("]}");
    }
    close(fd);
}

int main(int argc, char **argv) {
    int interval = argc > 1 ? atoi(argv[1]) : 1;
    for (;;) {
        DIR *d = opendir("/proc");
        struct dirent *e; int first = 1;
        printf("{\"source\":\"agent\",\"processes\":[");
        while (d && (e = readdir(d))) {
            int pid = atoi(e->d_name);
            if (pid <= 0) continue;
            if (!first) printf(",");
            dump_process(pid); first = 0;
        }
        printf("]}\n"); fflush(stdout);
        if (d) closedir(d);
        sleep(interval);
    }
}
