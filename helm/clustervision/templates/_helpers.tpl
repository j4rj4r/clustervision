{{/*
Expand the name of the chart.
*/}}
{{- define "clustervision.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "clustervision.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Namespace to deploy into.
*/}}
{{- define "clustervision.namespace" -}}
{{- if .Values.namespace.create -}}
{{- .Values.namespace.name }}
{{- else -}}
{{- .Release.Namespace }}
{{- end }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "clustervision.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
app.kubernetes.io/name: {{ include "clustervision.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Backend image tag — prefers .Values.backend.image.tag, falls back to appVersion.
*/}}
{{- define "clustervision.backendImage" -}}
{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
Frontend image tag — prefers .Values.frontend.image.tag, falls back to appVersion.
*/}}
{{- define "clustervision.frontendImage" -}}
{{ .Values.frontend.image.repository }}:{{ .Values.frontend.image.tag | default .Chart.AppVersion }}
{{- end }}

{{/*
ServiceAccount name
*/}}
{{- define "clustervision.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (printf "%s-backend" (include "clustervision.fullname" .)) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
