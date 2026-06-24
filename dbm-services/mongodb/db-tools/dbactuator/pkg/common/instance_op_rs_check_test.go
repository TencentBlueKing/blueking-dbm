package common

import "testing"

func TestValidateRsAvailabilityBeforeRestart(t *testing.T) {
	members3 := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 1, StateStr: "SECONDARY"},
	}
	if err := ValidateRsAvailabilityBeforeRestart(members3, "127.0.0.2:27017"); err != nil {
		t.Fatalf("expected healthy 3-node restart to pass: %v", err)
	}

	unhealthyOther := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 0, StateStr: "DOWN"},
	}
	if err := ValidateRsAvailabilityBeforeRestart(unhealthyOther, "127.0.0.2:27017"); err == nil {
		t.Fatal("expected failure when another member is unhealthy")
	}

	members5 := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.4:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.5:27017", Health: 0, StateStr: "DOWN"},
	}
	if err := ValidateRsAvailabilityBeforeRestart(members5, "127.0.0.2:27017"); err == nil {
		t.Fatal("expected failure when another member is down in 5-node rs")
	}

	onlyTwoHealthy := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 0, StateStr: "DOWN"},
	}
	if err := ValidateRsAvailabilityBeforeRestart(onlyTwoHealthy, "127.0.0.2:27017"); err == nil {
		t.Fatal("expected failure when another member is unhealthy")
	}
	if err := ValidateRsAvailabilityBeforeRestart(onlyTwoHealthy, "127.0.0.1:27017"); err == nil {
		t.Fatal("expected failure when restarting would not leave strict majority")
	}
	if err := ValidateRsAvailabilityBeforeRestart(onlyTwoHealthy, "127.0.0.3:27017"); err != nil {
		t.Fatalf("restarting an already-down member should pass when others are healthy: %v", err)
	}

	psaMembers := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 1, StateStr: "ARBITER"},
	}
	if err := ValidateRsAvailabilityBeforeRestart(psaMembers, "127.0.0.2:27017"); err != nil {
		t.Fatalf("expected PSA secondary restart to pass with healthy arbiter: %v", err)
	}
}

func TestValidateRsAllMembersReady(t *testing.T) {
	allReady := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 1, StateStr: "SECONDARY"},
		{Name: "127.0.0.3:27017", Health: 1, StateStr: "ARBITER"},
	}
	if err := ValidateRsAllMembersReady(allReady); err != nil {
		t.Fatalf("expected all members ready: %v", err)
	}

	notReady := []rsStatusMember{
		{Name: "127.0.0.1:27017", Health: 1, StateStr: "PRIMARY"},
		{Name: "127.0.0.2:27017", Health: 0, StateStr: "DOWN"},
	}
	if err := ValidateRsAllMembersReady(notReady); err == nil {
		t.Fatal("expected failure when a member is not PRIMARY/SECONDARY/ARBITER ready")
	}
}
