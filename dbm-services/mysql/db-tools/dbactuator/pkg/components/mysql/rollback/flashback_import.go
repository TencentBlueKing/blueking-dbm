package rollback

// ImportBinlog TODO
func (f *Flashback) ImportBinlog() error {
	return f.recover.Import()
}
