/*

 MIT License

 (C) Copyright 2023 Hewlett Packard Enterprise Development LP

 Permission is hereby granted, free of charge, to any person obtaining a
 copy of this software and associated documentation files (the "Software"),
 to deal in the Software without restriction, including without limitation
 the rights to use, copy, modify, merge, publish, distribute, sublicense,
 and/or sell copies of the Software, and to permit persons to whom the
 Software is furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included
 in all copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.

*/

package crucible

import (
	"fmt"
	"github.com/Cray-HPE/crucible/pkg/cmd/cli/install"
	"github.com/Cray-HPE/crucible/pkg/cmd/cli/network"
	"github.com/Cray-HPE/crucible/pkg/cmd/cli/storage"
	"github.com/Cray-HPE/crucible/pkg/version"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
	"log"
)

var newArgs []string

// NewCommand creates the `crucible` main command.
func NewCommand(name string) *cobra.Command {
	c := &cobra.Command{
		Use:   name,
		Short: fmt.Sprintf("Hyper-converged infrastructure management(%s)", name),
		Long: fmt.Sprintf(`
%[1]s bare-metal and virtualized control for hyper-converged infrastructure. %[1]s provides an
interface for bare-metal installations, configuration, and virtual machine deployment.
`, name),
		Version: version.Version(),
		PersistentPreRun: func(c *cobra.Command, args []string) {
			v := viper.GetViper()
			bindErr := v.BindPFlags(c.Flags())
			if bindErr != nil {
				log.Fatalf("Error reading command line: %s", bindErr)
			}
		},
	}
	c.PersistentFlags().StringP(
		"config",
		"c",
		fmt.Sprintf("./%s.yml", name),
		fmt.Sprintf("`%s.yml` Configuration file.", name))
	c.AddCommand(
		install.NewCommand(),
		network.NewCommand(),
		storage.NewCommand(),
	)

	return c
}
