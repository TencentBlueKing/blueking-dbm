package util

import (
	"encoding/xml"
)

// ConfigMap TODO
type ConfigMap map[string]string

// Configuration TODO
type Configuration struct {
	XMLName  xml.Name      `xml:"configuration"`
	Property []PropertyXml `xml:"property"`
}

// PropertyXml TODO
type PropertyXml struct {
	Name  string `xml:"name"`
	Value string `xml:"value"`
}

// TransMap2Xml TODO
func TransMap2Xml(configMap ConfigMap) ([]byte, error) {

	var properties []PropertyXml
	for k, v := range configMap {
		properties = append(properties, PropertyXml{
			Name:  k,
			Value: v,
		})
	}
	byteData, err := xml.MarshalIndent(Configuration{
		Property: properties,
	}, "  ", "  ")

	return append([]byte(xml.Header), byteData...), err
}
