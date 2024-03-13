package jobruntime

// JobRunner defines a behavior of a job
type JobRunner interface {
	// Init doing some operation before run a job
	// such as reading parametes
	Init(*JobGenericRuntime) error

	// Name return the name of the job
	Name() string

	// Run run a job
	Run() error

	Retry() uint

	// Rollback you can define some rollback logic here when job fails
	Rollback() error

	Param() string
}
