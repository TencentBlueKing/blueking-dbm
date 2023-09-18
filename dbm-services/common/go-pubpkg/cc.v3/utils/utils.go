// Package utils TODO
package utils

import (
	"reflect"
	"strings"
)

// GetStructTagName TODO
func GetStructTagName(t reflect.Type) []string {
	var tags []string
	switch t.Kind() {
	case reflect.Array, reflect.Chan, reflect.Map, reflect.Ptr, reflect.Slice:
		for _, item := range GetStructTagName(t.Elem()) {
			tags = append(tags, toTagName(item))
		}
	case reflect.Struct:
		for i := 0; i < t.NumField(); i++ {
			f := t.Field(i)
			switch f.Type.Kind() {
			case reflect.Array, reflect.Chan, reflect.Map, reflect.Ptr, reflect.Slice:
				for _, item := range GetStructTagName(f.Type) {
					tags = append(tags, toTagName(item))
				}
			}
			if f.Tag != "" {
				tags = append(tags, toTagName(f.Tag.Get("json")))
			}
		}
	}
	return tags
}

func toTagName(val string) string {
	parts := strings.Split(val, ",")
	if len(parts) > 0 {
		return parts[0]
	}
	return val
}
