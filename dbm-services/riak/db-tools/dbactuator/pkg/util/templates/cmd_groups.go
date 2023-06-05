package templates

import (
	"github.com/spf13/cobra"
)

// CommandGroup TODO
type CommandGroup struct {
	Message  string
	Commands []*cobra.Command
}

// CommandGroups TODO
type CommandGroups []CommandGroup

// Add TODO
func (g CommandGroups) Add(c *cobra.Command) {
	for _, group := range g {
		c.AddCommand(group.Commands...)
	}
}
