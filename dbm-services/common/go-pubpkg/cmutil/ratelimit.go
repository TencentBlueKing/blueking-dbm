package cmutil

import (
	"io"

	"github.com/juju/ratelimit"
)

// IOLimitRate io.Copy limit io rate
// if bwlimitMB=0, not limit
func IOLimitRate(dst io.Writer, src io.Reader, bwlimitMB int64) (written int64, err error) {
	if bwlimitMB == 0 {
		bufTmp := make([]byte, 128*1024)
		return io.CopyBuffer(dst, src, bufTmp)
		//return io.Copy(dst, src)
	}
	buf := make([]byte, 128*1024) // not use default 32 * 1024
	bwlimit := bwlimitMB * 1024 * 1024
	srcBucket := ratelimit.NewBucketWithRate(float64(bwlimit), bwlimit)
	return io.CopyBuffer(dst, ratelimit.Reader(src, srcBucket), buf)
}

// IOLimitRateWithChunk io.Copy limit io rate
// if bwlimitMB=0, not limit
// if chunkSize > src size, err=EOF
func IOLimitRateWithChunk(dst io.Writer, src io.Reader, bwlimitMB int64, chunkSize int64) (written int64, err error) {
	if bwlimitMB == 0 {
		bufTmp := make([]byte, 128*1024)
		return io.CopyBuffer(dst, src, bufTmp)
		// return io.Copy(dst, src)
	}
	bwlimit := bwlimitMB * 1024 * 1024
	srcBucket := ratelimit.NewBucketWithRate(float64(bwlimit), bwlimit)
	return io.CopyN(dst, ratelimit.Reader(src, srcBucket), chunkSize)
}
