package rollback

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"
)

func TestTuningWritesOnlyItsEnginesDirectives(t *testing.T) {
	if got := (plusTuning{}).Directives(128); !reflect.DeepEqual(got,
		map[string]string{"rocks.write_buffer_size": "134217728"}) {
		t.Fatalf("plus: %v", got)
	}
	// 0 keeps the template's; compaction and the WAL are never touched.
	if got := (plusTuning{}).Directives(0); len(got) != 0 {
		t.Fatalf("plus 0: %v", got)
	}
	for _, tuning := range []Tuning{cacheTuning{}, ssdTuning{}} {
		if got := tuning.Directives(128); len(got) != 0 {
			t.Fatalf("%s: %v", tuning.Name(), got)
		}
	}
}

func TestNewPicksTheEnginesTuning(t *testing.T) {
	for dbType, want := range map[string]string{
		"PredixyTendisplusCluster":   "tendisplus",
		"TwemproxyRedisInstance":     "cache",
		"TwemproxyTendisSSDInstance": "tendisssd",
	} {
		r, err := New(dbType, Job{})
		if err != nil {
			t.Fatalf("%s: %v", dbType, err)
		}
		var job Job
		switch v := r.(type) {
		case *plusRestorer:
			job = v.Job
		case *cacheRestorer:
			job = v.Job
		case *ssdRestorer:
			job = v.Job
		}
		if job.tuning == nil || job.tuning.Name() != want {
			t.Fatalf("%s: tuning %v, want %s", dbType, job.tuning, want)
		}
	}
}

func TestApplyTuningRewritesTheConfBeforeStart(t *testing.T) {
	host := dirHost{root: t.TempDir()}
	conf := confFile(host.InstanceDir(30000))
	_ = os.MkdirAll(filepath.Dir(conf), 0755)
	template := "rocks.blockcachemb 1024\nrocks.write_buffer_size 67108864\nkvstorecount 10\n"
	if err := os.WriteFile(conf, []byte(template), 0644); err != nil {
		t.Fatal(err)
	}
	job := Job{Host: host, tuning: plusTuning{}, WriteBufferMB: 128}
	if err := job.applyTuning([]int{30000}); err != nil {
		t.Fatal(err)
	}
	raw, _ := os.ReadFile(conf)
	content := string(raw)
	if strings.Count(content, "rocks.write_buffer_size") != 1 || !strings.Contains(content, "rocks.write_buffer_size 134217728") ||
		strings.Contains(content, "disable_auto_compactions") || strings.Contains(content, "disable_wal") {
		t.Fatalf("conf:\n%s", content)
	}
	// the memory window reads the tuned buffer: block cache plus two buffers per kvstore
	if got, want := PlusMemory(conf), int64(1024<<20+10*2*128<<20); got != want {
		t.Fatalf("memory %d, want %d", got, want)
	}
	if got := job.tuningSummary(); got != "rocks.write_buffer_size=134217728" {
		t.Fatalf("summary %q", got)
	}

	// an older payload sends 0: the conf stays as rendered
	_ = os.WriteFile(conf, []byte(template), 0644)
	job.WriteBufferMB = 0
	if err := job.applyTuning([]int{30000}); err != nil {
		t.Fatal(err)
	}
	if raw, _ = os.ReadFile(conf); string(raw) != template || job.tuningSummary() != "" {
		t.Fatalf("conf changed with 0:\n%s", raw)
	}
}

func TestPlusTunedMemoryOverTheWindowFailsTheStart(t *testing.T) {
	conf := filepath.Join(t.TempDir(), "redis.conf")
	_ = os.WriteFile(conf, []byte("rocks.blockcachemb 1024\nrocks.write_buffer_size 134217728\nkvstorecount 10\n"), 0644)
	// 4GiB available leaves 3.6GiB: one 3.5GiB instance fits, a second does not
	w := newMemWindow(4<<30, 2)
	if err := w.reserve(PlusMemory(conf)); err != nil {
		t.Fatal(err)
	}
	if err := w.reserve(PlusMemory(conf)); err == nil || !strings.Contains(err.Error(), "not enough memory") {
		t.Fatalf("err=%v", err)
	}
}

func TestRestoredHowLooksAtTheUnpackedCopy(t *testing.T) {
	root := writeBackup(t, 0, 1)
	if got := restoredHow(root, 2); got != restoredCopied {
		t.Fatalf("kvstores still unpacked: %s", got)
	}
	// looking renames and removes nothing: the backup is as unpacked
	if metas, err := readPlusBackupMetas(root); err != nil || len(metas) != 2 || metas[1].BinlogPos != 101 {
		t.Fatalf("backup changed: %v %v", metas, err)
	}
	_ = os.RemoveAll(filepath.Join(root, "0"))
	if got := restoredHow(root, 2); got != restoredCopied {
		t.Fatalf("one kvstore left: %s", got)
	}
	_ = os.RemoveAll(filepath.Join(root, "1"))
	if got := restoredHow(root, 2); got != restoredMoved {
		t.Fatalf("all moved: %s", got)
	}
}

// fakeProc writes a /proc entry for pid running args, with utime/stime/starttime in ticks.
func fakeProc(t *testing.T, root string, pid int, args []string, utime, stime, start uint64) {
	t.Helper()
	dir := filepath.Join(root, fmt.Sprint(pid))
	_ = os.MkdirAll(dir, 0755)
	_ = os.WriteFile(filepath.Join(dir, "cmdline"), []byte(strings.Join(args, "\x00")+"\x00"), 0644)
	// fields 3..22: state ppid pgrp session tty tpgid flags minflt cminflt majflt cmajflt utime stime
	// cutime cstime priority nice threads itrealvalue starttime
	stat := fmt.Sprintf("%d (tendis plus) S 1 1 1 0 -1 0 0 0 0 0 %d %d 0 0 20 0 8 0 %d 0 0\n", pid, utime, stime, start)
	_ = os.WriteFile(filepath.Join(dir, "stat"), []byte(stat), 0644)
}

func TestProcessByArgAndItsCPU(t *testing.T) {
	root := t.TempDir()
	procRoot = root
	defer func() { procRoot = "/proc" }()
	fakeProc(t, root, 100, []string{"/usr/local/redis/bin/tendisplus", "/data1/redis/30001/redis.conf"}, 1, 1, 7)
	fakeProc(t, root, 200, []string{"/usr/local/redis/bin/tendisplus", "/data1/redis/30000/redis.conf"}, 150, 50, 9)
	pid, start, err := ProcessByArg("/data1/redis/30000/redis.conf")
	if err != nil || pid != 200 || start != 9 {
		t.Fatalf("pid=%d start=%d err=%v", pid, start, err)
	}
	if cpu, err := processCPU(pid, start); err != nil || cpu != 2*time.Second {
		t.Fatalf("cpu=%v err=%v", cpu, err)
	}
	// a restarted instance has another start time: its CPU is not this one's
	fakeProc(t, root, 200, []string{"/usr/local/redis/bin/tendisplus", "/data1/redis/30000/redis.conf"}, 1, 0, 99)
	if _, err = processCPU(pid, start); err == nil {
		t.Fatal("want error for a restarted process")
	}
	if _, _, err = ProcessByArg("/data1/redis/30002/redis.conf"); err == nil {
		t.Fatal("want error without the process")
	}
}

// procHost runs its instances as fake /proc entries.
type procHost struct {
	dirHost
	pid int
}

func (h procHost) ProcessID(int) (int, uint64, error) { return h.pid, 9, nil }

func TestPlusReplayBooksTheInstanceCPU(t *testing.T) {
	root := t.TempDir()
	procRoot = root
	defer func() { procRoot = "/proc" }()
	fakeProc(t, root, 300, []string{"tendisplus"}, 100, 0, 9)

	fake := map[int]*portReplayer{}
	r, chains, restore := plusPorts(t, map[int]int{30000: 1}, fake)
	defer restore()
	r.Host = procHost{dirHost: r.Host.(dirHost), pid: 300}
	defer scriptTool(t, func(_, kvstore int, start uint64, onLine func(string) error) error {
		// the instance works while the replay runs
		fakeProc(t, root, 300, []string{"tendisplus"}, 400, 100, 9)
		return onLine(restoreLine(kvstore, start))
	})()
	inst := InstanceRestore{DestPort: 30000}
	p := newHostReport(r.DestIP, "tendisplus", []InstanceRestore{inst}).port(30000)
	if err := r.replayAndMark(inst, p, chains[30000], time.Time{}, make(chan struct{}, 1)); err != nil {
		t.Fatal(err)
	}
	if p.instanceCPU != 4*time.Second {
		t.Fatalf("instance cpu %v", p.instanceCPU)
	}
	// apply is the instance's CPU over the replay plus the actuator's sending the batches
	if apply := p.cpu[stageApply]; apply < 4*time.Second || apply >= 5*time.Second {
		t.Fatalf("apply cpu %v", apply)
	}
}

func TestRestoreBooksTheInstanceCPU(t *testing.T) {
	root := t.TempDir()
	procRoot = root
	defer func() { procRoot = "/proc" }()
	fakeProc(t, root, 300, []string{"tendisplus"}, 100, 0, 9)
	j := Job{Host: procHost{dirHost: dirHost{root: t.TempDir()}, pid: 300}}
	p := newHostReport("2.2.2.2", enginePlus, []InstanceRestore{{DestPort: 30000}}).port(30000)
	err := j.timedOnInstance(portLog{}, p, 30000, stageRestore, func() error {
		// restorebackup runs inside the instance
		fakeProc(t, root, 300, []string{"tendisplus"}, 400, 100, 9)
		return nil
	})
	if err != nil || p.cpu[stageRestore] != 4*time.Second || p.durations[stageRestore] <= 0 {
		t.Fatalf("err=%v cpu=%v durations=%v", err, p.cpu, p.durations)
	}

	// an instance that cannot be read books no CPU and still fails as fn does
	j.Host = dirHost{root: t.TempDir()}
	p = newHostReport("2.2.2.2", enginePlus, []InstanceRestore{{DestPort: 30000}}).port(30000)
	err = j.timedOnInstance(newPortLog(30000), p, 30000, stageRestore, func() error { return fmt.Errorf("boom") })
	if err == nil || p.cpu[stageRestore] != 0 {
		t.Fatalf("err=%v cpu=%v", err, p.cpu)
	}
}

func TestSummariesShowKvstoresTuningAndRestore(t *testing.T) {
	h := newHostReport("2.2.2.2", "tendisplus", []InstanceRestore{{DestPort: 30000, SourceIP: "1.1.1.1", SourcePort: 30000}})
	h.tuning = "rocks.write_buffer_size=134217728"
	p := h.port(30000)
	p.setRestored(restoredCopied)
	p.setInstanceCPU(90 * time.Second)
	p.addKvstore(0, stageParse, 0, 3*time.Second)
	p.addKvstore(0, stageDecode, 4*time.Second, 5*time.Second)
	p.addKvstore(0, stageApply, 6*time.Second, 0)
	p.kvstoreReplayed(0, 36, 1000, 391911, 392911)
	p.kvstoreAfter(0, 392911)
	p.finish(nil)
	text := h.resultText() + "\n" + h.diagText(p, "")
	for _, want := range []string{
		"cpu: actuator ",
		", instances 1m30s",
		"tuning: rocks.write_buffer_size=134217728",
		"30000  done         -       -       -      4s      6s",
		"         cpu        -       -      3s      5s       -",
		" full backup copied; instance cpu 1m30s",
		"    0   36       391911 -> 392911               -     3s     4s     6s",
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("missing %q in:\n%s", want, text)
		}
	}
	// a port whose instance CPU was never read leaves it out
	h = newHostReport("2.2.2.2", "tendisplus", []InstanceRestore{{DestPort: 30000}})
	h.port(30000).finish(nil)
	if text := h.resultText() + h.diagText(h.port(30000), ""); strings.Contains(text, "instance") {
		t.Fatalf("unsampled instance cpu shown:\n%s", text)
	}
}
