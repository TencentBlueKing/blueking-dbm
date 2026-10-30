package kafka

import (
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

// writePropertiesFile is a small test helper writing lines to a temp server.properties file.
func writePropertiesFile(t *testing.T, dir string, lines ...string) string {
	t.Helper()
	filePath := filepath.Join(dir, "server.properties")
	if err := os.WriteFile(filePath, []byte(strings.Join(lines, "\n")+"\n"), 0644); err != nil {
		t.Fatalf("failed to write test properties file: %v", err)
	}
	return filePath
}

// readLines reads back a file's non-empty lines for assertions.
func readLines(t *testing.T, filePath string) []string {
	t.Helper()
	content, err := os.ReadFile(filePath)
	if err != nil {
		t.Fatalf("failed to read file: %v", err)
	}
	var lines []string
	for _, line := range strings.Split(string(content), "\n") {
		if line != "" {
			lines = append(lines, line)
		}
	}
	return lines
}

// TestDeleteConfigLines_StripsAclConfigOnNoSecurity verifies that when a cluster runs with
// no_security=1 (no authentication, every connection is ANONYMOUS), authorizer.class.name,
// super.users and allow.everyone.if.no.acl.found are all removed from the rendered config —
// otherwise ACL's deny-by-default would reject every client.
func TestDeleteConfigLines_StripsAclConfigOnNoSecurity(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"broker.id=1",
		"sasl.enabled.mechanisms=SCRAM-SHA-512",
		"sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512",
		"security.inter.broker.protocol=SASL_PLAINTEXT",
		"authorizer.class.name=kafka.security.authorizer.AclAuthorizer",
		"super.users=User:test_admin;User:kafka",
		"allow.everyone.if.no.acl.found=false",
		"listeners=BROKER://1.1.1.1:9092",
	)

	keys := append([]string{
		"sasl.enabled.mechanisms",
		"sasl.mechanism.inter.broker.protocol",
		"security.inter.broker.protocol",
	}, aclConfigKeys...)
	if err := deleteConfigLines(filePath, keys); err != nil {
		t.Fatalf("deleteConfigLines failed: %v", err)
	}

	lines := readLines(t, filePath)
	for _, forbidden := range []string{
		"authorizer.class.name=", "super.users=", "allow.everyone.if.no.acl.found=",
		"sasl.enabled.mechanisms=", "sasl.mechanism.inter.broker.protocol=", "security.inter.broker.protocol=",
	} {
		for _, line := range lines {
			if strings.HasPrefix(line, forbidden) {
				t.Fatalf("expected %q to be stripped, still present: %q", forbidden, line)
			}
		}
	}
	// unrelated lines must survive untouched
	found := map[string]bool{"broker.id=1": false, "listeners=BROKER://1.1.1.1:9092": false}
	for _, line := range lines {
		if _, ok := found[line]; ok {
			found[line] = true
		}
	}
	for line, ok := range found {
		if !ok {
			t.Fatalf("expected unrelated line %q to survive, got: %v", line, lines)
		}
	}
}

// TestDeleteConfigLines_ControllerKeepsAclConfig verifies the KRaft controller-only code path only
// strips broker-inter-broker SASL keys, and leaves authorizer.class.name/super.users/
// allow.everyone.if.no.acl.found in place. Kafka requires an authorizer configured on controllers
// too (cluster-management and ACL-management requests are authorized there), so — unlike the
// no_security path — ACL config must never be blanket-deleted for a controller-only node.
func TestDeleteConfigLines_ControllerKeepsAclConfig(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"node.id=1",
		"sasl.enabled.mechanisms=SCRAM-SHA-512",
		"sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512",
		"inter.broker.listener.name=BROKER",
		"authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer",
		"super.users=User:test_admin;User:kafka",
		"allow.everyone.if.no.acl.found=false",
		"process.roles=controller",
	)

	keys := []string{
		"sasl.enabled.mechanisms",
		"sasl.mechanism.inter.broker.protocol",
		"inter.broker.listener.name",
	}
	if err := deleteConfigLines(filePath, keys); err != nil {
		t.Fatalf("deleteConfigLines failed: %v", err)
	}

	lines := readLines(t, filePath)
	for _, forbidden := range []string{
		"sasl.enabled.mechanisms=", "sasl.mechanism.inter.broker.protocol=", "inter.broker.listener.name=",
	} {
		for _, line := range lines {
			if strings.HasPrefix(line, forbidden) {
				t.Fatalf("expected %q to be stripped, still present: %q", forbidden, line)
			}
		}
	}
	for _, expected := range []string{
		"authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer",
		"super.users=User:test_admin;User:kafka",
		"allow.everyone.if.no.acl.found=false",
		"node.id=1",
		"process.roles=controller",
	} {
		found := false
		for _, line := range lines {
			if line == expected {
				found = true
				break
			}
		}
		if !found {
			t.Fatalf("expected ACL/unrelated line %q to survive, got: %v", expected, lines)
		}
	}
}

// TestDeleteConfigLines_DoesNotMatchSubstringOrComment ensures matching is anchored to the start
// of the line (leading whitespace allowed) rather than matching "key=" anywhere in the line — a
// comment or an unrelated key that happens to contain the target key as a substring must survive.
func TestDeleteConfigLines_DoesNotMatchSubstringOrComment(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"# authorizer.class.name=commented out, should survive",
		"my.authorizer.class.name=should survive, not a real prefix match",
		"authorizer.class.name=kafka.security.authorizer.AclAuthorizer",
	)

	if err := deleteConfigLines(filePath, []string{"authorizer.class.name"}); err != nil {
		t.Fatalf("deleteConfigLines failed: %v", err)
	}

	lines := readLines(t, filePath)
	if len(lines) != 2 {
		t.Fatalf("expected the 2 non-matching lines to survive, got: %v", lines)
	}
	for _, expected := range []string{
		"# authorizer.class.name=commented out, should survive",
		"my.authorizer.class.name=should survive, not a real prefix match",
	} {
		found := false
		for _, line := range lines {
			if line == expected {
				found = true
			}
		}
		if !found {
			t.Fatalf("expected line %q to survive, got: %v", expected, lines)
		}
	}
}

// TestAppendSuperUser_AddsPrincipal verifies the controller-only helper that grants the
// CONTROLLER listener's ANONYMOUS principal super-user trust without touching any other line.
func TestAppendSuperUser_AddsPrincipal(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"node.id=1",
		"super.users=User:test_admin;User:kafka",
		"authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer",
	)

	if err := appendSuperUser(filePath, "User:ANONYMOUS"); err != nil {
		t.Fatalf("appendSuperUser failed: %v", err)
	}

	lines := readLines(t, filePath)
	found := false
	for _, line := range lines {
		if line == "super.users=User:test_admin;User:kafka;User:ANONYMOUS" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected super.users line to have ANONYMOUS appended, got: %v", lines)
	}
}

// TestAppendSuperUser_MissingLineReturnsError ensures a missing super.users line fails loudly
// instead of silently installing a controller without the intended ANONYMOUS grant.
func TestAppendSuperUser_MissingLineReturnsError(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir, "node.id=1")
	if err := appendSuperUser(filePath, "User:ANONYMOUS"); err == nil {
		t.Fatalf("expected an error when super.users line is missing")
	}
}

// TestAppendSuperUser_AlreadyPresentIsNoop ensures re-appending a principal that's already in
// super.users (e.g. a hand-edited dbconfig template) doesn't duplicate it.
func TestAppendSuperUser_AlreadyPresentIsNoop(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"node.id=1",
		"super.users=User:test_admin;User:kafka;User:ANONYMOUS",
	)

	if err := appendSuperUser(filePath, "User:ANONYMOUS"); err != nil {
		t.Fatalf("appendSuperUser failed: %v", err)
	}

	lines := readLines(t, filePath)
	for _, line := range lines {
		if line == "super.users=User:test_admin;User:kafka;User:ANONYMOUS" {
			return
		}
	}
	t.Fatalf("expected super.users line to be unchanged (no duplicate), got: %v", lines)
}

// TestConfigHasKey_PresentReturnsTrue verifies configHasKey finds a top-level key line.
func TestConfigHasKey_PresentReturnsTrue(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"node.id=1",
		"authorizer.class.name=org.apache.kafka.metadata.authorizer.StandardAuthorizer",
	)

	has, err := configHasKey(filePath, "authorizer.class.name")
	if err != nil {
		t.Fatalf("configHasKey failed: %v", err)
	}
	if !has {
		t.Fatalf("expected authorizer.class.name to be found")
	}
}

// TestConfigHasKey_AbsentReturnsFalse verifies configHasKey reports false rather than erroring
// when a key is entirely missing — the exact shape of a pre-ACL dbconfig template. This is the
// scenario the caller relies on to safely skip the controller ACL adjustment for old configs
// instead of erroring, keeping a newer dbactuator compatible with a not-yet-updated dbconfig.
func TestConfigHasKey_AbsentReturnsFalse(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir, "node.id=1", "process.roles=controller")

	has, err := configHasKey(filePath, "authorizer.class.name")
	if err != nil {
		t.Fatalf("configHasKey failed: %v", err)
	}
	if has {
		t.Fatalf("expected authorizer.class.name to be reported absent")
	}
}

// TestConfigHasKey_DoesNotMatchSubstringOrComment ensures matching is anchored to the start of the
// line, mirroring deleteConfigLines' own matching rule.
func TestConfigHasKey_DoesNotMatchSubstringOrComment(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"# authorizer.class.name=commented out, should not count",
		"my.authorizer.class.name=should not count, not a real prefix match",
	)

	has, err := configHasKey(filePath, "authorizer.class.name")
	if err != nil {
		t.Fatalf("configHasKey failed: %v", err)
	}
	if has {
		t.Fatalf("expected authorizer.class.name to be reported absent (only substring/comment matches present)")
	}
}

// TestControllerAclAdjustment_OldDbconfig_StripsSaslWithoutSuperUser exercises the same sequence
// InstallBroker's controller-role branch runs against a rendered config that came from a pre-ACL
// dbconfig template (no authorizer.class.name, no super.users at all): the sasl/inter-broker-listener
// deletion is unconditional controller-only behavior that predates the ACL feature entirely, so it
// must still run and succeed; only the super.users/ANONYMOUS append is ACL-specific and must be
// skipped rather than erroring. Regression test for a bug where the sasl/inter-broker-listener
// deletion was mistakenly nested inside the authorizer.class.name check, so old dbconfig configs
// would keep their broker-only sasl/inter-broker-listener settings instead of having them stripped.
func TestControllerAclAdjustment_OldDbconfig_StripsSaslWithoutSuperUser(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir,
		"node.id=1",
		"process.roles=controller",
		"sasl.enabled.mechanisms=SCRAM-SHA-512",
		"sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512",
		"inter.broker.listener.name=BROKER",
	)

	if err := deleteConfigLines(filePath, []string{
		"sasl.enabled.mechanisms",
		"sasl.mechanism.inter.broker.protocol",
		"inter.broker.listener.name",
	}); err != nil {
		t.Fatalf("deleteConfigLines failed: %v", err)
	}

	hasAuthorizer, err := configHasKey(filePath, "authorizer.class.name")
	if err != nil {
		t.Fatalf("configHasKey failed: %v", err)
	}
	if hasAuthorizer {
		t.Fatalf("expected authorizer.class.name to be absent for a pre-ACL dbconfig fixture")
	}
	// mirrors InstallBroker: appendSuperUser only runs when hasAuthorizer is true, so for this
	// pre-ACL fixture it must be skipped entirely rather than called (and erroring on the missing
	// super.users line).

	lines := readLines(t, filePath)
	for _, forbidden := range []string{
		"sasl.enabled.mechanisms=", "sasl.mechanism.inter.broker.protocol=", "inter.broker.listener.name=",
	} {
		for _, line := range lines {
			if strings.HasPrefix(line, forbidden) {
				t.Fatalf("expected %q to be stripped regardless of ACL, still present: %q", forbidden, line)
			}
		}
	}
	for _, line := range lines {
		if strings.HasPrefix(line, "super.users=") {
			t.Fatalf("expected no super.users line to be introduced for a pre-ACL dbconfig, got: %q", line)
		}
	}
	found := false
	for _, line := range lines {
		if line == "node.id=1" {
			found = true
		}
	}
	if !found {
		t.Fatalf("expected unrelated line %q to survive, got: %v", "node.id=1", lines)
	}
}

// TestDeleteConfigLines_NoKeysIsNoop ensures an empty key list leaves the file untouched.
func TestDeleteConfigLines_NoKeysIsNoop(t *testing.T) {
	dir := t.TempDir()
	filePath := writePropertiesFile(t, dir, "broker.id=1")

	if err := deleteConfigLines(filePath, nil); err != nil {
		t.Fatalf("deleteConfigLines failed: %v", err)
	}

	lines := readLines(t, filePath)
	if len(lines) != 1 || lines[0] != "broker.id=1" {
		t.Fatalf("expected file untouched, got: %v", lines)
	}
}

// TestKafkaUIClusterEnv_ZKMode verifies a ZK broker config yields both SUPERUSERS and ZOOKEEPERCONNECT,
// taken verbatim from the rendered config.
func TestKafkaUIClusterEnv_ZKMode(t *testing.T) {
	filePath := writePropertiesFile(t, t.TempDir(),
		"broker.id=1",
		"super.users=User:test_admin;User:kafka",
		"zookeeper.connect=127.0.0.1:2181,127.0.0.2:2181,127.0.0.3:2181/",
	)
	got, err := kafkaUIClusterEnv(filePath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	for _, want := range []string{
		"export KAFKA_CLUSTERS_0_SUPERUSERS='User:test_admin;User:kafka'\n",
		"export KAFKA_CLUSTERS_0_ZOOKEEPERCONNECT='127.0.0.1:2181,127.0.0.2:2181,127.0.0.3:2181/'\n",
	} {
		if !strings.Contains(got, want) {
			t.Errorf("missing %q in:\n%s", want, got)
		}
	}
}

// TestKafkaUIClusterEnv_KRaftMode verifies a KRaft config (no zookeeper.connect, and a commented-out
// one must not count) gets SUPERUSERS only — ZOOKEEPERCONNECT must never be set for KRaft.
func TestKafkaUIClusterEnv_KRaftMode(t *testing.T) {
	filePath := writePropertiesFile(t, t.TempDir(),
		"process.roles=broker",
		"super.users=User:test_admin;User:kafka",
		"#zookeeper.connect=127.0.0.1:2181/",
	)
	got, err := kafkaUIClusterEnv(filePath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(got, "KAFKA_CLUSTERS_0_SUPERUSERS='User:test_admin;User:kafka'") {
		t.Errorf("missing SUPERUSERS in:\n%s", got)
	}
	if strings.Contains(got, "ZOOKEEPERCONNECT") {
		t.Errorf("ZOOKEEPERCONNECT must not be set for KRaft, got:\n%s", got)
	}
}

// TestKafkaUIClusterEnv_NoSuperUsers verifies a config without super.users (e.g. no-security) is not an
// error and emits no SUPERUSERS line; a missing file is an error.
func TestKafkaUIClusterEnv_NoSuperUsers(t *testing.T) {
	dir := t.TempDir()
	got, err := kafkaUIClusterEnv(writePropertiesFile(t, dir, "broker.id=1", "super.users="))
	if err != nil || got != "" {
		t.Fatalf("expected empty env and nil error, got %q, %v", got, err)
	}
	if _, err := kafkaUIClusterEnv(filepath.Join(dir, "missing.properties")); err == nil {
		t.Fatal("expected error for missing file")
	}
}

// TestKafkaUIClusterEnv_ShellRoundTrip sources the generated env through bash and checks the values
// come back unchanged, including a single quote that would otherwise break the file.
func TestKafkaUIClusterEnv_ShellRoundTrip(t *testing.T) {
	if _, err := exec.LookPath("bash"); err != nil {
		t.Skip("bash not available")
	}
	const superUsers = "User:ops'admin;User:kafka"
	const zkConnect = "127.0.0.1:2181,127.0.0.2:2181/it's"
	filePath := writePropertiesFile(t, t.TempDir(),
		"super.users="+superUsers,
		"zookeeper.connect="+zkConnect,
	)
	got, err := kafkaUIClusterEnv(filePath)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	envFile := filepath.Join(t.TempDir(), "kafkaui.sh")
	if err := os.WriteFile(envFile, []byte(got), 0644); err != nil {
		t.Fatalf("write env file: %v", err)
	}
	out, err := exec.Command("bash", "-c",
		`. "$1" && printf '%s\n%s' "$KAFKA_CLUSTERS_0_SUPERUSERS" "$KAFKA_CLUSTERS_0_ZOOKEEPERCONNECT"`,
		"_", envFile).CombinedOutput()
	if err != nil {
		t.Fatalf("sourcing generated env failed: %v\n%s", err, out)
	}
	if want := superUsers + "\n" + zkConnect; string(out) != want {
		t.Errorf("round-trip mismatch:\n got %q\nwant %q", out, want)
	}
}
