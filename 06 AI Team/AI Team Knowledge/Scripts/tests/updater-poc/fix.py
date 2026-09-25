import os, shutil, stat
from pathlib import PurePosixPath
def _dir_fd_nofollow(root, parent):
    fd = os.open(str(root), os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in PurePosixPath(parent).parts:
            try:
                nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            except FileNotFoundError:
                os.mkdir(part, 0o755, dir_fd=fd)
                nfd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nfd
        return fd
    except BaseException:
        os.close(fd); raise
def write_atomic(src, root, rel):
    p = PurePosixPath(rel)
    dfd = _dir_fd_nofollow(root, p.parent)
    tmp = ".mypka-update-%s.tmp" % os.urandom(6).hex()
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        with os.fdopen(fd, "wb") as out, open(src, "rb") as inp:
            shutil.copyfileobj(inp, out)
        os.chmod(tmp, stat.S_IMODE(os.stat(src).st_mode) & 0o755, dir_fd=dfd)
        os.replace(tmp, p.name, src_dir_fd=dfd, dst_dir_fd=dfd)
    except BaseException:
        try: os.unlink(tmp, dir_fd=dfd)
        except FileNotFoundError: pass
        raise
    finally:
        os.close(dfd)
