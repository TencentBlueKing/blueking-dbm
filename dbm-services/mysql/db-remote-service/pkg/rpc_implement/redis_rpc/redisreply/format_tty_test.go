package redisreply

import (
	"testing"
)

func TestCliFormatReplyTTY0(t *testing.T) {
	o := FormatReplyTTY(false, int64(3), "")
	t.Log("\n|\n" + o)

	o = FormatReplyTTY(false, "string", "")
	t.Log("\n|\n" + o)

	o = FormatReplyTTY(true, "OK", "")
	t.Log("\n|\n" + o)
	o = FormatReplyTTY(true, make([]interface{}, 0), "")
	t.Log("\n|\n" + o)
}

func TestCliFormatReplyTTY(t *testing.T) {
	strs := []string{"first", "second", "3", "4", "5", "6", "7", "8", "9", "19", "200"}
	interface2 := make([]interface{}, 0)
	for i := range strs {
		interface2 = append(interface2, strs[i])
	}

	o := FormatReplyTTY(false, interface2, "")
	t.Log("\n|\n" + o)
}

func TestCliFormatReplyTTY2(t *testing.T) {
	strs := []string{"first", "second", "3", "4", "5", "6", "7", "8", "9", "19", "200"}
	interface1 := make([]interface{}, 0)
	interface2 := make([]interface{}, 0)
	interface3 := make([]interface{}, 0)

	for i := range strs {
		interface2 = append(interface2, strs[i])
		interface3 = append(interface3, strs[i])
	}
	interface1 = append(interface1, interface2, interface3)

	o := FormatReplyTTY(false, interface1, "")
	t.Log("\n|\n" + o)
}

func TestCliFormatReplyTTY3(t *testing.T) {
	strs := []string{"first", "second", "3", "4", "5", "6", "7", "8", "9", "19", "200"}
	interface1 := make([]interface{}, 0)
	interface2 := make([]interface{}, 0)
	interface3 := make([]interface{}, 0)

	for i := 0; i < len(strs); i++ {
		interface3 = append(interface3, strs[i])
	}
	interface2 = append(interface2, interface3)
	for i := 0; i < 2; i++ {
		interface2 = append(interface2, int64(i))
	}
	interface1 = append(interface1, interface2)
	interface1 = append(interface1, interface2)

	o := FormatReplyTTY(false, interface1, "")
	t.Log("\n" + o)
}
