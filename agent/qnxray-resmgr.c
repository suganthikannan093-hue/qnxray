/*
 * qnxray-resmgr: QNXray collector as a QNX resource manager.
 * Registers /dev/qnxray; every open() takes a fresh system snapshot (same JSON
 * schema as qnxray-agent) and read() streams it, so `cat /dev/qnxray` works.
 * Each client gets its own snapshot buffer in an extended OCB, so concurrent
 * readers see consistent data. Run as root:  qnxray-resmgr [-p path] [-n] (-n: no daemonize)
 * Build: qcc -Vgcc_ntox86_64 -DQNXRAY_NO_MAIN -o qnxray-resmgr qnxray-resmgr.c qnxray-agent.c
 */
#define _POSIX_C_SOURCE 200809L
#define _QNX_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>

struct qx_ocb;
#define IOFUNC_OCB_T struct qx_ocb
#include <sys/iofunc.h>
#include <sys/dispatch.h>
#include <sys/procmgr.h>

struct qx_ocb { iofunc_ocb_t hdr; char *buf; size_t len; };

void qnxray_snapshot(FILE *f, const char *source);

static iofunc_attr_t attr;

static struct qx_ocb *qx_calloc(resmgr_context_t *ctp, iofunc_attr_t *a) {
    (void)ctp; (void)a;
    struct qx_ocb *o = calloc(1, sizeof *o);
    if (!o) return NULL;
    FILE *f = tmpfile();                 /* QNX libc has no open_memstream */
    if (f) {
        qnxray_snapshot(f, "resmgr");
        long n = ftell(f); rewind(f);
        if (n > 0 && (o->buf = malloc(n))) o->len = fread(o->buf, 1, n, f);
        fclose(f);
    }
    return o;
}
static void qx_free(struct qx_ocb *o) { free(o->buf); free(o); }

static iofunc_funcs_t ocb_funcs = { _IOFUNC_NFUNCS, qx_calloc, qx_free };
static iofunc_mount_t qx_mount = { .funcs = &ocb_funcs };

static int qx_read(resmgr_context_t *ctp, io_read_t *msg, struct qx_ocb *o) {
    int st = iofunc_read_verify(ctp, msg, &o->hdr, NULL);
    if (st != EOK) return st;
    if ((msg->i.xtype & _IO_XTYPE_MASK) != _IO_XTYPE_NONE) return ENOSYS;
    size_t off = o->hdr.offset, n = 0;
    if (off < o->len) {
        n = o->len - off;
        if (n > _IO_READ_GET_NBYTES(msg)) n = _IO_READ_GET_NBYTES(msg);
    }
    _IO_SET_READ_NBYTES(ctp, n);
    o->hdr.offset += n;
    if (n) { SETIOV(ctp->iov, o->buf + off, n); return _RESMGR_NPARTS(1); }
    return _RESMGR_NPARTS(0);
}

int main(int argc, char **argv) {
    const char *path = "/dev/qnxray"; int daemon = 1, c;
    while ((c = getopt(argc, argv, "p:n")) != -1) {
        if (c == 'p') path = optarg; else if (c == 'n') daemon = 0;
    }
    dispatch_t *dpp = dispatch_create();
    if (!dpp) { perror("dispatch_create"); return 1; }
    static resmgr_connect_funcs_t cf; static resmgr_io_funcs_t iof;
    iofunc_func_init(_RESMGR_CONNECT_NFUNCS, &cf, _RESMGR_IO_NFUNCS, &iof);
    iof.read = qx_read;
    iofunc_attr_init(&attr, S_IFNAM | 0444, NULL, NULL);
    attr.mount = &qx_mount;
    resmgr_attr_t ra; memset(&ra, 0, sizeof ra); ra.nparts_max = 1; ra.msg_max_size = 2048;
    if (resmgr_attach(dpp, &ra, path, _FTYPE_ANY, 0, &cf, &iof, &attr) == -1) {
        perror("resmgr_attach"); return 1;
    }
    fprintf(stderr, "qnxray-resmgr: serving %s\n", path);
    if (daemon && procmgr_daemon(EXIT_SUCCESS, 0) == -1) {
        perror("procmgr_daemon"); return 1;
    }
    dispatch_context_t *ctp = dispatch_context_alloc(dpp);
    for (;;) { if ((ctp = dispatch_block(ctp))) dispatch_handler(ctp); }
}
