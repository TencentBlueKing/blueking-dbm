/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 */

package workflow

import (
	"strconv"
	"testing"
)

// TestConsistentHash_Stability verifies that the same instance set always
// produces the same assignment for a given business ID.
func TestConsistentHash_Stability(t *testing.T) {
	instances := []string{"inst-A", "inst-B", "inst-C"}
	bizIDs := []int{101, 102, 103, 104, 105, 106, 107, 108, 109, 110}

	// Build hash ring multiple times and verify consistent results
	for round := 0; round < 10; round++ {
		ch := newConsistentHash(defaultReplicas)
		ch.rebuild(instances)

		for _, bizID := range bizIDs {
			key := strconv.Itoa(bizID)
			owner1 := ch.get(key)
			owner2 := ch.get(key)

			if owner1 != owner2 {
				t.Errorf("round %d: inconsistent assignment for bizID %d: got %s and %s",
					round, bizID, owner1, owner2)
			}
		}
	}

	// Verify different rebuilds produce same results
	ch1 := newConsistentHash(defaultReplicas)
	ch1.rebuild(instances)

	ch2 := newConsistentHash(defaultReplicas)
	ch2.rebuild(instances)

	for _, bizID := range bizIDs {
		key := strconv.Itoa(bizID)
		owner1 := ch1.get(key)
		owner2 := ch2.get(key)

		if owner1 != owner2 {
			t.Errorf("different ring builds gave different assignments for bizID %d: %s vs %s",
				bizID, owner1, owner2)
		}
	}
}

// TestConsistentHash_Coverage verifies that all business IDs are assigned
// to some instance (no business is left unassigned).
func TestConsistentHash_Coverage(t *testing.T) {
	instances := []string{"inst-A", "inst-B", "inst-C", "inst-D"}
	bizIDs := make([]int, 1000)

	for i := 0; i < 1000; i++ {
		bizIDs[i] = i + 1
	}

	ch := newConsistentHash(defaultReplicas)
	ch.rebuild(instances)

	assigned := make(map[string][]int)

	for _, bizID := range bizIDs {
		key := strconv.Itoa(bizID)
		owner := ch.get(key)

		if owner == "" {
			t.Errorf("bizID %d was not assigned to any instance", bizID)
			continue
		}

		assigned[owner] = append(assigned[owner], bizID)
	}

	// Verify all instances have some assignments
	for _, inst := range instances {
		if len(assigned[inst]) == 0 {
			t.Errorf("instance %s has no assignments", inst)
		}
	}

	// Verify total assignments equals total businesses
	total := 0
	for _, bids := range assigned {
		total += len(bids)
	}

	if total != len(bizIDs) {
		t.Errorf("total assigned (%d) != total bizIDs (%d)", total, len(bizIDs))
	}

	t.Logf("Distribution across %d instances:", len(instances))
	for inst, bids := range assigned {
		t.Logf("  %s: %d businesses (%.1f%%)", inst, len(bids), float64(len(bids))/float64(len(bizIDs))*100)
	}
}

// TestConsistentHash_ScalingMigration verifies that adding/removing instances
// causes minimal redistribution (approximately 1/N instead of (N-1)/N).
func TestConsistentHash_ScalingMigration(t *testing.T) {
	bizIDs := make([]int, 10000)
	for i := 0; i < 10000; i++ {
		bizIDs[i] = i + 1
	}

	testCases := []struct {
		name         string
		before       []string
		after        []string
		maxMigration float64 // maximum acceptable migration ratio
	}{
		{
			name:         "3->4 instances (add one)",
			before:       []string{"inst-A", "inst-B", "inst-C"},
			after:        []string{"inst-A", "inst-B", "inst-C", "inst-D"},
			maxMigration: 0.40, // should be around 25%, allow some margin
		},
		{
			name:         "4->3 instances (remove one)",
			before:       []string{"inst-A", "inst-B", "inst-C", "inst-D"},
			after:        []string{"inst-A", "inst-B", "inst-C"},
			maxMigration: 0.40, // should be around 25%, allow some margin
		},
		{
			name:         "5->6 instances",
			before:       []string{"inst-A", "inst-B", "inst-C", "inst-D", "inst-E"},
			after:        []string{"inst-A", "inst-B", "inst-C", "inst-D", "inst-E", "inst-F"},
			maxMigration: 0.30, // should be around 16.7%
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			chBefore := newConsistentHash(defaultReplicas)
			chBefore.rebuild(tc.before)

			chAfter := newConsistentHash(defaultReplicas)
			chAfter.rebuild(tc.after)

			migrated := 0

			for _, bizID := range bizIDs {
				key := strconv.Itoa(bizID)
				ownerBefore := chBefore.get(key)
				ownerAfter := chAfter.get(key)

				if ownerBefore != ownerAfter {
					migrated++
				}
			}

			migrationRatio := float64(migrated) / float64(len(bizIDs))
			t.Logf("Migration: %d/%d (%.2f%%)", migrated, len(bizIDs), migrationRatio*100)

			if migrationRatio > tc.maxMigration {
				t.Errorf("migration ratio %.2f%% exceeds maximum %.2f%%",
					migrationRatio*100, tc.maxMigration*100)
			}
		})
	}
}

// TestConsistentHash_EmptyRing verifies behavior with empty ring.
func TestConsistentHash_EmptyRing(t *testing.T) {
	ch := newConsistentHash(defaultReplicas)

	owner := ch.get("123")
	if owner != "" {
		t.Errorf("expected empty string for empty ring, got %s", owner)
	}
}

// TestInstanceDiscovery_AssignedBizIDs verifies the AssignedBizIDs method.
func TestInstanceDiscovery_AssignedBizIDs(t *testing.T) {
	bizIDs := []int{101, 102, 103, 104, 105, 106, 107, 108, 109, 110}

	// Create three instance discoveries representing three instances
	instances := []string{"inst-A", "inst-B", "inst-C"}
	discoveries := make([]*InstanceDiscovery, len(instances))

	for i, instID := range instances {
		discoveries[i] = NewInstanceDiscovery(nil, "/test/prefix", instID, make(chan struct{}))
		discoveries[i].hashRing.rebuild(instances)
	}

	// Collect all assigned bizIDs from all instances
	allAssigned := make(map[int]string)

	for _, d := range discoveries {
		assigned := d.AssignedBizIDs(bizIDs)

		for _, bizID := range assigned {
			if prev, exists := allAssigned[bizID]; exists {
				t.Errorf("bizID %d assigned to multiple instances: %s and %s", bizID, prev, d.myServiceID)
			}
			allAssigned[bizID] = d.myServiceID
		}
	}

	// Verify all bizIDs are assigned
	for _, bizID := range bizIDs {
		if _, exists := allAssigned[bizID]; !exists {
			t.Errorf("bizID %d was not assigned to any instance", bizID)
		}
	}

	t.Logf("Total bizIDs: %d, All assigned: %d", len(bizIDs), len(allAssigned))
}

// TestInstanceDiscovery_EmptyHashRing verifies fallback behavior.
func TestInstanceDiscovery_EmptyHashRing(t *testing.T) {
	d := &InstanceDiscovery{
		myServiceID: "inst-A",
		hashRing:    newConsistentHash(defaultReplicas),
	}

	// Empty hash ring should return all bizIDs
	bizIDs := []int{101, 102, 103}
	assigned := d.AssignedBizIDs(bizIDs)

	if len(assigned) != len(bizIDs) {
		t.Errorf("expected all bizIDs for empty ring, got %d/%d", len(assigned), len(bizIDs))
	}
}

// TestConsistentHash_LoadBalance verifies reasonable load distribution.
func TestConsistentHash_LoadBalance(t *testing.T) {
	instances := []string{"inst-A", "inst-B", "inst-C", "inst-D", "inst-E"}
	bizIDs := make([]int, 10000)

	for i := 0; i < 10000; i++ {
		bizIDs[i] = i + 1
	}

	ch := newConsistentHash(defaultReplicas)
	ch.rebuild(instances)

	counts := make(map[string]int)

	for _, bizID := range bizIDs {
		owner := ch.get(strconv.Itoa(bizID))
		counts[owner]++
	}

	expectedPerInstance := float64(len(bizIDs)) / float64(len(instances))
	maxDeviation := 0.50 // allow 50% deviation; load balance is secondary to migration minimization

	for inst, count := range counts {
		deviation := float64(count)/expectedPerInstance - 1.0
		if deviation < 0 {
			deviation = -deviation
		}

		t.Logf("Instance %s: %d (%.1f%% of expected)",
			inst, count, float64(count)/expectedPerInstance*100)

		if deviation > maxDeviation {
			t.Errorf("instance %s has too much deviation: %.1f%% (max allowed: %.1f%%)",
				inst, deviation*100, maxDeviation*100)
		}
	}
}
