{{/*
This function is used to format a line to the log format, so that it can be saved into a log file.

Usage:
    format_log_content SOME_TYPE SOME_COMPONENT
Result:
    The line to be logged will be formatted with some logging information, and be printed to the stdout
Example:
    echo "some line content from stdout" | format_log_content STDOUT SOME_COMPONENT > /path/to/logfile
    echo "some line content from stderr" | format_log_content STDERR SOME_COMPONENT > /path/to/logfile
*/}}
{{- define "kblib.logs.format_log_content" }}
format_log_content() {
    local content_type #STDOUT or STDERR
    local component
    content_type=$1
    component=$2
    while IFS= read -r line; do
        echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') [$content_type] [$component] $line"
    done
}
{{- end }}

{{/*
This function is used to setup the logging of the script, 
so that the STDOUT/STDERR of the scripts can be recorded into a dedicated file.

Usage:
    setup_logging LOG_COMPONENT LOG_FILE
Result:
    The stdout / stderr of the script will be saved into a dedicated file
Example:
    setup_logging SOME_COMPONENT dummy.log
*/}}
{{- define "kblib.logs.setup_logging" }}
setup_logging() {
    local component
    local log_file
    component=$1
    log_file=$2

    # redirect all the stdout and stderr to files
    exec > >( tee >( format_log_content STDOUT "${component}" | stdbuf -oL cat >> "${log_file}" ) ) \
        2> >( tee >( format_log_content STDERR "${component}" | stdbuf -oL cat >> "${log_file}" ) >&2 )
}
{{- end }}
