// Command demo_stream_oplog_zstd demonstrates how to stream mongodump's
// dump/local/oplog.rs.bson output directly into zstd without creating a
// normal uncompressed oplog.rs.bson file.
//
// It uses a FIFO (named pipe) at the exact path mongodump wants to write:
//
//	mongodump --out <workdir>/dump  -->  <workdir>/dump/local/oplog.rs.bson (FIFO)
//	zstd <workdir>/dump/local/oplog.rs.bson -o <workdir>/oplog.rs.bson.zst
//
// The FIFO is only a kernel pipe endpoint. Data flows through it to zstd; it is
// not a regular BSON file on disk.
//
// This is a development-only demo script; do not use default credentials in production.
package main

import (
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"time"
)

func main() {
	host := flag.String("host", "127.0.0.1", "MongoDB host")
	port := flag.String("port", "27002", "MongoDB port")
	user := flag.String("user", "root", "MongoDB user")
	pass := flag.String("pass", "root", "MongoDB password")
	authDB := flag.String("authdb", "admin", "MongoDB auth database")
	workdir := flag.String("workdir", "", "work directory; default is a temp dir")
	flag.Parse()

	if *workdir == "" {
		tmp, err := os.MkdirTemp("/tmp", "demo-stream-oplog-zstd-")
		must(err)
		*workdir = tmp
	}

	dumpDir := filepath.Join(*workdir, "dump")
	localDir := filepath.Join(dumpDir, "local")
	fifoPath := filepath.Join(localDir, "oplog.rs.bson")
	zstPath := filepath.Join(*workdir, "oplog.rs.bson.zst")
	decodedPath := filepath.Join(*workdir, "oplog.rs.bson.from-zst")
	must(os.MkdirAll(localDir, 0755))

	// This is the key trick: mongodump thinks it is writing dump/local/oplog.rs.bson,
	// but that path is a FIFO, so bytes go straight to zstd.
	must(syscall.Mkfifo(fifoPath, 0600))

	startSec := time.Now().Unix()
	endSec := startSec + 60
	query := fmt.Sprintf(
		`{"ts":{"$gte":{"$timestamp":{"t":%d,"i":0}},"$lte":{"$timestamp":{"t":%d,"i":999}}}}`,
		startSec,
		endSec,
	)

	zstdCmd := exec.Command("zstd", "-f", fifoPath, "-o", zstPath)
	zstdCmd.Stdout = os.Stdout
	zstdCmd.Stderr = os.Stderr
	must(zstdCmd.Start())

	dumpCmd := exec.Command(
		"mongodump",
		"--host", *host,
		"--port", *port,
		"--username", *user,
		"--password", *pass,
		"--authenticationDatabase", *authDB,
		"-d", "local",
		"-c", "oplog.rs",
		"-q", query,
		"--out", dumpDir,
	)
	dumpCmd.Stdout = os.Stdout
	dumpCmd.Stderr = os.Stderr

	fmt.Printf("workdir: %s\n", *workdir)
	fmt.Printf("fifo:    %s\n", fifoPath)
	fmt.Printf("zstd:    %s\n", zstPath)
	fmt.Printf("query:   %s\n", query)
	must(dumpCmd.Run())
	must(zstdCmd.Wait())

	// Optional decode step: keep a BSON file for inspection.
	decodeCmd := exec.Command("zstd", "-d", "-f", "-k", zstPath, "-o", decodedPath)
	decodeCmd.Stdout = os.Stdout
	decodeCmd.Stderr = os.Stderr
	must(decodeCmd.Run())

	fmt.Println("done")
	fmt.Printf("compressed zstd: %s\n", zstPath)
	fmt.Printf("decoded bson:    %s\n", decodedPath)
	fmt.Println("note: dump/local/oplog.rs.bson is a FIFO, not a regular BSON file")
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
