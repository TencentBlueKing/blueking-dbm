package atommongodb

import "testing"

func TestParseMongoVersionTuple(t *testing.T) {
	tuple, err := parseMongoVersionTuple("mongodb-6.0.6")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if tuple.major != 6 || tuple.minor != 0 || tuple.patch != 6 || !tuple.hasPatch {
		t.Fatalf("unexpected tuple: %+v", tuple)
	}

	mmOnly, err := parseMongoVersionTuple("6.0")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if mmOnly.hasPatch {
		t.Fatalf("expected major.minor only tuple: %+v", mmOnly)
	}
}

func TestCompareMongoVersionTuplesPatchUpgrade(t *testing.T) {
	left, _ := parseMongoVersionTuple("6.0.6")
	right, _ := parseMongoVersionTuple("6.0.27")
	if compareMongoVersionTuples(left, right) >= 0 {
		t.Fatalf("expected 6.0.6 < 6.0.27")
	}
	if compareMongoVersionTuples(right, right) != 0 {
		t.Fatalf("expected equal versions")
	}
}

func TestCompareMongoVersionTuplesMajorMinorAsPatchZero(t *testing.T) {
	full, _ := parseMongoVersionTuple("6.0.27")
	mmOnly, _ := parseMongoVersionTuple("6.0")
	if compareMongoVersionTuples(full, mmOnly) <= 0 {
		t.Fatalf("expected 6.0.27 > 6.0")
	}
	if compareMongoVersionTuples(mmOnly, full) >= 0 {
		t.Fatalf("expected 6.0 < 6.0.27")
	}
}
