package components

// BaseInputParam TODO
type BaseInputParam struct {
	GeneralParam *GeneralParam `json:"general"`
	ExtendParam  interface{}   `json:"extend"`
}

// GeneralParam TODO
type GeneralParam struct {
	RuntimeAccountParam RuntimeAccountParam `json:"runtime_account"`
	// more Runtime Struct
}

// RuntimeAccountParam TODO
type RuntimeAccountParam struct {
}
