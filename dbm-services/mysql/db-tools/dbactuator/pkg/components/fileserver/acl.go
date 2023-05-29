package fileserver

import (
	"fmt"
	"net"
	"strings"
)

// ACL TODO
type ACL struct {
	Action string `json:"action"`
	Who    string `json:"who"`
	Rule   string `json:"rule"`
}

// checkACL godoc
// TODO 允许 1.1.1.1 1.1.1.1/32 都合法
func checkACL(acls []string, remoteAddr net.Addr, clientAddr string) error {
	if len(acls) == 0 {
		return nil
	}
	var remoteIP net.IP
	if clientAddr == "" {
		clientAddr = remoteAddr.String()
	}
	host, _, err := net.SplitHostPort(clientAddr)
	if err != nil {
		return fmt.Errorf("BUG: invalid remote address %q", clientAddr)
	}
	remoteIP = net.ParseIP(host)
	if remoteIP == nil {
		return fmt.Errorf("BUG: invalid remote host %s", host)
	}
	for _, acl := range acls {
		// TODO(performance): move ACL parsing to config-time to make ACL checks
		// less expensive
		i := strings.Index(acl, " ")
		if i < 0 {
			return fmt.Errorf("invalid acl: %q (no space found)", acl)
		}
		action, who := acl[:i], acl[i+len(" "):]
		if action != "allow" && action != "deny" {
			return fmt.Errorf("invalid acl: %q (syntax: allow|deny <all|ipnet>)", acl)
		}
		if who == "all" {
			// The all keyword matches any remote IP address
		} else {
			_, net, err := net.ParseCIDR(who)
			if err != nil {
				return fmt.Errorf("invalid acl: %q (syntax: allow|deny <all|ipnet>)", acl)
			}
			if !net.Contains(remoteIP) {
				// Skip this instruction, the remote IP does not match
				continue
			}
		}
		switch action {
		case "allow":
			return nil
		case "deny":
			return fmt.Errorf("access denied (acl %q)", acl)
		default:
			return fmt.Errorf("invalid acl: %q (syntax: allow|deny <all|ipnet>)", acl)
		}
	}
	return nil
}
