package haprobe

import "testing"

func TestDbEventNameMapContainsRedisV1Events(t *testing.T) {
	expected := []DbEventName{
		DbEventNameDetectRedisAuthFailureV1,
		DbEventNameRedisSwitchSuccessV1,
		DbEventNameRedisSwitchFailureV1,
	}

	for _, eventName := range expected {
		if _, exists := DbEventNameMap[eventName]; !exists {
			t.Fatalf("event missing in map: %s", eventName)
		}
	}
}

func TestDisabledDBSupportedEnum(t *testing.T) {
	expected := []DbType{
		DbTypeMySql,
		DbTypeRedis,
		DbTypeSqlServer,
		DbTypeMongo,
		DbTypeRiak,
		DbTypeHdfs,
		DbTypeEs,
		DbTypeKafka,
		DbTypeDoris,
		DbTypePulsar,
	}
	if len(DisabledDBSupportedEnum) != len(expected) {
		t.Fatalf("unexpected disabled db enum size: %d", len(DisabledDBSupportedEnum))
	}

	for idx, dbType := range expected {
		if DisabledDBSupportedEnum[idx] != dbType {
			t.Fatalf("unexpected enum at index %d: %s", idx, DisabledDBSupportedEnum[idx])
		}
	}
}

func TestIsSwitchControllableDbType(t *testing.T) {
	if !IsSwitchControllableDbType(DbTypeMySql) {
		t.Fatal("mysql should be switch controllable")
	}
	if !IsSwitchControllableDbType(DbTypeRedis) {
		t.Fatal("redis should be switch controllable")
	}
	if !IsSwitchControllableDbType(DbTypeKafka) {
		t.Fatal("kafka should be switch controllable")
	}
	if IsSwitchControllableDbType(DbTypeUnknown) {
		t.Fatal("unknown should not be switch controllable")
	}
	if IsSwitchControllableDbType(DbTypeNone) {
		t.Fatal("none should not be switch controllable")
	}
}
