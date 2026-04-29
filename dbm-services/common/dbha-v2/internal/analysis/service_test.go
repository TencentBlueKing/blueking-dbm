package analysis

import "testing"

func TestResolveBkMonitorEndpoint(t *testing.T) {
	t.Parallel()

	testCases := []struct {
		name    string
		raw     string
		want    string
		wantErr bool
	}{
		{
			name:    "domain socket path",
			raw:     "/var/run/bkmonitor.sock",
			want:    "/var/run/bkmonitor.sock",
			wantErr: false,
		},
		{
			name:    "domain socket path with spaces",
			raw:     "  /var/run/bkmonitor.sock  ",
			want:    "/var/run/bkmonitor.sock",
			wantErr: false,
		},
		{
			name:    "host port",
			raw:     "127.0.0.1:9090",
			want:    "127.0.0.1:9090",
			wantErr: false,
		},
		{
			name:    "http endpoint",
			raw:     "http://127.0.0.1:9090",
			want:    "127.0.0.1:9090",
			wantErr: false,
		},
		{
			name:    "empty endpoint",
			raw:     "   ",
			want:    "",
			wantErr: true,
		},
		{
			name:    "invalid endpoint",
			raw:     "bk-monitor-endpoint",
			want:    "",
			wantErr: true,
		},
	}

	for _, tc := range testCases {
		tc := tc
		t.Run(tc.name, func(t *testing.T) {
			t.Parallel()

			got, err := resolveBkMonitorEndpoint(tc.raw)
			if (err != nil) != tc.wantErr {
				t.Fatalf("resolveBkMonitorEndpoint() error = %v, wantErr = %v", err, tc.wantErr)
			}

			if got != tc.want {
				t.Fatalf("resolveBkMonitorEndpoint() = %q, want = %q", got, tc.want)
			}
		})
	}
}
