import type { SidebarsConfig } from "@docusaurus/plugin-content-docs";

const sidebar: SidebarsConfig = {
  apisidebar: [
    {
      type: "doc",
      id: "api/ai-interview-orchestrator",
    },
    {
      type: "category",
      label: "Health",
      items: [
        {
          type: "doc",
          id: "api/health-check-health-get",
          label: "Health Check",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/liveness-probe-livez-get",
          label: "Liveness Probe",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/readiness-probe-readyz-get",
          label: "Readiness Probe",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-system-health-system-health-get",
          label: "Get System Health",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-worker-health-worker-health-get",
          label: "Get Worker Health",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Metrics",
      items: [
        {
          type: "doc",
          id: "api/get-system-metrics-monitoring-metrics-system-get",
          label: "Get System Metrics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-worker-metrics-endpoint-monitoring-metrics-workers-get",
          label: "Get Worker Metrics Endpoint",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-metrics-endpoint-monitoring-metrics-sessions-get",
          label: "Get Session Metrics Endpoint",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-queue-metrics-monitoring-metrics-queue-get",
          label: "Get Queue Metrics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-failure-metrics-endpoint-monitoring-metrics-failures-get",
          label: "Get Failure Metrics Endpoint",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-retry-metrics-endpoint-monitoring-metrics-retries-get",
          label: "Get Retry Metrics Endpoint",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-performance-metrics-monitoring-metrics-performance-get",
          label: "Get Performance Metrics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-dashboard-summary-monitoring-metrics-dashboard-get",
          label: "Get Dashboard Summary",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/prometheus-metrics-metrics-get",
          label: "Prometheus Metrics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-dashboard-dashboard-get",
          label: "Get Dashboard",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/receive-web-vitals-metrics-web-vitals-post",
          label: "Receive Web Vitals",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Workers",
      items: [
        {
          type: "doc",
          id: "api/register-worker-register-worker-post",
          label: "Register Worker",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/worker-heartbeat-worker-heartbeat-post",
          label: "Worker Heartbeat",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/list-workers-workers-get",
          label: "List Workers",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-worker-stats-worker-statistics-get",
          label: "Get Worker Stats",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/deregister-worker-deregister-worker-worker-id-delete",
          label: "Deregister Worker",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "api/get-worker-distribution-worker-distribution-get",
          label: "Get Worker Distribution",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Candidates",
      items: [
        {
          type: "doc",
          id: "api/list-candidates-candidates-get",
          label: "List Candidates",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/create-candidate-candidates-post",
          label: "Create Candidate",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-candidate-candidates-candidate-id-get",
          label: "Get Candidate",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-candidate-history-candidates-candidate-id-history-get",
          label: "Get Candidate History",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Interviews",
      items: [
        {
          type: "doc",
          id: "api/start-interview-start-interview-post",
          label: "Start Interview",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-interview-report-interviews-session-id-report-get",
          label: "Get Interview Report",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/list-interviews-interviews-get",
          label: "List Interviews",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/ask-question-interviews-ask-question-post",
          label: "Ask Question",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/submit-answer-interviews-submit-answer-post",
          label: "Submit Answer",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Questions",
      items: [
        {
          type: "doc",
          id: "api/list-questions-questions-get",
          label: "List Questions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/add-question-questions-post",
          label: "Add Question",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Configurations",
      items: [
        {
          type: "doc",
          id: "api/list-configs-risk-configs-get",
          label: "List all risk weight configurations",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/create-config-risk-configs-post",
          label: "Create a risk weight configuration for a job position",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-config-risk-configs-config-id-get",
          label: "Get a specific risk weight configuration by ID",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/update-config-risk-configs-config-id-put",
          label: "Update a risk weight configuration",
          className: "api-method put",
        },
        {
          type: "doc",
          id: "api/delete-config-risk-configs-config-id-delete",
          label: "Delete a risk weight configuration",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "api/get-by-position-risk-configs-by-position-job-position-get",
          label: "Get risk weight configuration by job position name",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Scheduler",
      items: [
        {
          type: "doc",
          id: "api/get-scheduling-status-scheduling-status-get",
          label: "Get Scheduling Status",
          className: "api-method get",
        },
      ],
    },
    {
      type: "category",
      label: "Authentication",
      items: [
        {
          type: "doc",
          id: "api/login-login-post",
          label: "Login",
          className: "api-method post",
        },
      ],
    },
    {
      type: "category",
      label: "Other",
      items: [
        {
          type: "doc",
          id: "api/get-dependency-statuses-dependencies-get",
          label: "Get Dependency Statuses",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-circuit-breaker-status-circuit-breaker-get",
          label: "Get Circuit Breaker Status",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-status-session-status-session-id-get",
          label: "Get Session Status",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-risk-report-session-status-session-id-risk-report-get",
          label: "Get Session Risk Report",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-task-status-task-status-task-id-get",
          label: "Get Task Status",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-active-sessions-active-sessions-get",
          label: "Get Active Sessions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-completed-sessions-completed-sessions-get",
          label: "Get Completed Sessions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-stuck-sessions-stuck-sessions-get",
          label: "Get Stuck Sessions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-statistics-session-statistics-get",
          label: "Get Session Statistics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-high-risk-sessions-high-risk-sessions-get",
          label: "Get High Risk Sessions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-failed-sessions-failed-sessions-get",
          label: "Get Failed Sessions",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/retry-failed-session-retry-session-session-id-post",
          label: "Retry Failed Session",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-recovery-queue-recovery-queue-get",
          label: "Get Recovery Queue",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-failure-log-failure-log-get",
          label: "Get Failure Log",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-dead-letter-queue-dead-letter-queue-get",
          label: "Get Dead Letter Queue",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-fault-statistics-fault-statistics-get",
          label: "Get Fault Statistics",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/detect-and-handle-failures-detect-failures-post",
          label: "Detect And Handle Failures",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/list-templates-templates-get",
          label: "List Templates",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/create-template-templates-post",
          label: "Create Template",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-load-status-load-status-get",
          label: "Get Load Status",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-fairness-audit-report-admin-fairness-audit-get",
          label: "Get Fairness Audit Report",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-cache-stats-cache-stats-get",
          label: "Get Cache Stats",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/sync-cache-to-database-sync-to-database-post",
          label: "Sync Cache To Database",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/clear-session-cache-clear-cache-delete",
          label: "Clear Session Cache",
          className: "api-method delete",
        },
        {
          type: "doc",
          id: "api/switch-load-balancing-strategy-switch-strategy-post",
          label: "Switch Load Balancing Strategy",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/track-moment-moments-track-post",
          label: "Track Moment",
          className: "api-method post",
        },
        {
          type: "doc",
          id: "api/get-session-moments-moments-session-id-get",
          label: "Get Session Moments",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-timeline-moments-session-id-timeline-get",
          label: "Get Session Timeline",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-session-moment-summary-moments-session-id-summary-get",
          label: "Get Session Moment Summary",
          className: "api-method get",
        },
        {
          type: "doc",
          id: "api/get-moment-analytics-moments-analytics-get",
          label: "Get Moment Analytics",
          className: "api-method get",
        },
      ],
    },
  ],
};

export default sidebar.apisidebar;
