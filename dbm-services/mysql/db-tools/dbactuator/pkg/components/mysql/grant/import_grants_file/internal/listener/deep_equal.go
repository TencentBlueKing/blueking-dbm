package listener

import "slices"

func (c *PrivListener) DeepEqualWith(other *PrivListener) bool {
	if c.RawSQL == other.RawSQL {
		return true
	}

	if c.StatementType != other.StatementType {
		return false
	}
	switch c.StatementType {
	case PrivStatementCreate:
		return c.deepEqualCreate(other)
	case PrivStatementGrant:
		return c.deepEqualGrant(other)
	}
	return false
}

/*
createUser

	: CREATE USER userAuthOption (',' userAuthOption)* # createUserMysqlV56
	| CREATE USER ifNotExists? userAuthOption (',' userAuthOption)* (
	    REQUIRE (tlsNone = NONE | tlsOption (AND? tlsOption)*)
	)? (WITH userResourceOption+)? (userPasswordOption | userLockOption)* (
	    COMMENT STRING_LITERAL
	    | ATTRIBUTE STRING_LITERAL
	)? # createUserMysqlV80
	;
*/
func (c *PrivListener) deepEqualCreate(other *PrivListener) bool {
	// uerAuthOptions
	if !equalStringSlices(c.authOptionStrings, other.authOptionStrings) {
		return false
	}
	// tlsOption
	if (c.TlsNone == nil && other.TlsNone != nil) || (c.TlsNone != nil && other.TlsNone == nil) {
		return false
	}
	if !equalStringSlices(c.TlsOptions, other.TlsOptions) {
		return false
	}
	// userResourceOption
	if !equalStringSlices(c.ResourceOptions, other.ResourceOptions) {
		return false
	}
	// userPasswordOption, userLockOption
	if c.PasswordLockOption != other.PasswordLockOption {
		return false
	}
	return true
}

func (c *PrivListener) deepEqualGrant(other *PrivListener) bool {
	if c.GrantType != other.GrantType {
		return false
	}
	switch c.GrantType {
	case GrantStatementTypeNormal:
		return c.deepEqualGrantNormal(other)
	case GrantStatementTypeRole:
		return c.deepEqualGrantRole(other)
	case GrantStatementTypeProxy:
		return c.deepEqualGrantProxy(other)
	}
	return false
}

/*
: GRANT privelegeClause (',' privelegeClause)* ON privilegeObject = (

	TABLE
	| FUNCTION
	| PROCEDURE

)? privilegeLevel TO userAuthOption (',' userAuthOption)* (

	REQUIRE (tlsNone = NONE | tlsOption (AND? tlsOption)*)

)? (WITH (GRANT OPTION | userResourceOption)*)? (AS userName WITH ROLE roleOption)?
*/
func (c *PrivListener) deepEqualGrantNormal(other *PrivListener) bool {
	// privelegeClause
	if c.Privileges != other.Privileges {
		return false
	}
	// privilegeObject
	if c.PrivObject != other.PrivObject {
		return false
	}
	// privilegeLevel
	if c.DBName != other.DBName {
		return false
	}
	if c.TableName != other.TableName {
		return false
	}
	// userAuthOption
	if !equalStringSlices(c.authOptionStrings, other.authOptionStrings) {
		return false
	}
	// tlsOption
	if (c.TlsNone == nil && other.TlsNone != nil) || (c.TlsNone != nil && other.TlsNone == nil) {
		return false
	}
	if !equalStringSlices(c.TlsOptions, other.TlsOptions) {
		return false
	}
	// userResourceOption
	if !equalStringSlices(c.ResourceOptions, other.ResourceOptions) {
		return false
	}
	// roleOption
	if c.RoleOption != other.RoleOption {
		return false
	}
	// withGrantOption
	if c.WithGrantOption != other.WithGrantOption {
		return false
	}
	return true
}

/*
GRANT (userName | uid) (',' (userName | uid))* TO (userName | uid) (',' (userName | uid))* (

	    WITH ADMIN OPTION
	)?
*/
func (c *PrivListener) deepEqualGrantRole(other *PrivListener) bool {
	// FromUserOrIds
	if equalStringSlices(c.FromUserOrIds, other.FromUserOrIds) == false {
		return false
	}
	// ToUserOrIds
	if equalStringSlices(c.ToUserOrIds, other.ToUserOrIds) == false {
		return false
	}
	// WithAdminOption
	if c.WithAdminOption != other.WithAdminOption {
		return false
	}
	return true
}

/*
: GRANT PROXY ON fromFirst = userName TO toFirst = userName (',' toOther += userName)* (

	WITH GRANT OPTION

)?
;
*/
func (c *PrivListener) deepEqualGrantProxy(other *PrivListener) bool {
	// FromUsername
	if c.FromUsername != other.FromUsername {
		return false
	}
	// ToUsernames
	if equalStringSlices(c.ToUsernames, other.ToUsernames) == false {
		return false
	}
	// withGrantOption
	if c.WithGrantOption != other.WithGrantOption {
		return false
	}
	return true
}

func equalStringSlices(s1, s2 []string) bool {
	if s1 == nil && s2 == nil {
		return true
	}
	if len(s1) != len(s2) {
		return false
	}

	for _, s1v := range s1 {
		idx := slices.IndexFunc(s2, func(s2v string) bool {
			return s1v == s2v
		})
		if idx < 0 {
			return false
		}
	}

	for _, s2v := range s2 {
		idx := slices.IndexFunc(s1, func(s1v string) bool {
			return s1v == s2v
		})
		if idx < 0 {
			return false
		}
	}
	return true
}
