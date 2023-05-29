package xmlutil

import "encoding/xml"

// GenericMap TODO
type GenericMap map[string]interface{}

// MarshalXML TODO
func (g GenericMap) MarshalXML(e *xml.Encoder, start xml.StartElement) error {
	start.Name.Local = "performance_status"
	tokens := []xml.Token{start}
	tokens = ScanXMLNode(g, tokens)
	tokens = append(tokens, xml.EndElement{Name: start.Name})

	for _, t := range tokens {
		err := e.EncodeToken(t)
		if err != nil {
			return err
		}
	}
	// flush to ensure tokens are written
	err := e.Flush()
	if err != nil {
		return err
	}
	return nil
}

// ScanXMLNode TODO
func ScanXMLNode(g map[string]interface{}, tokens []xml.Token) []xml.Token {
	for key, value := range g {
		t := xml.StartElement{Name: xml.Name{Space: "", Local: key}}
		if mapInterface, ok := value.(map[string]interface{}); ok {
			haveAttr := false
			for k, v := range mapInterface { // k:check,expire_days v:
				if str, innerOk := v.(string); innerOk {
					t.Attr = append(t.Attr, xml.Attr{Name: xml.Name{Space: "", Local: k}, Value: str})
					haveAttr = true
				}
				// 暂时不考虑既有 child 是 map[string]string, 又是 map[string]map[string]interface{} 这种。
			}
			if haveAttr {
				tokens = append(tokens, t)
			} else {
				tokens = append(tokens, t)
				tokens = ScanXMLNode(mapInterface, tokens)
			}
		} else if mapString, ok := value.(map[string]string); ok {
			for k, v := range mapString {
				t.Attr = append(t.Attr, xml.Attr{Name: xml.Name{Space: "", Local: k}, Value: v})
			}
			tokens = append(tokens, t)
		} else {
			return nil
		}
		// fmt.Println("key end:", key)
		tokens = append(tokens, xml.EndElement{Name: xml.Name{Space: "", Local: key}})
	}
	return tokens
}
