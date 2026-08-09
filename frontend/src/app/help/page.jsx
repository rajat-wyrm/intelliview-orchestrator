export default function HelpPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-zinc-50">
          HR User Manual
        </h1>

        <p className="mt-2 text-sm text-muted">
          Welcome to the AI-IntelliView HR User Manual. This guide explains
          the main steps for managing candidates, starting interviews, and
          reviewing interview results.
        </p>
      </div>

      {/* 1. Adding Candidates */}
      <section className="rounded-lg border border-border bg-bg-card p-6">
        <h2 className="text-xl font-semibold text-zinc-50">
          1. Adding a Candidate
        </h2>

        <p className="mt-2 text-sm text-muted">
          HR users can add candidate information from the Recruiter Dashboard
          in the Analytics section.
        </p>

        <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-zinc-200">
          <li>Open the <strong>Analytics</strong> page from the sidebar.</li>
          <li>Find the <strong>Add Candidate</strong> section.</li>
          <li>Enter the candidate&apos;s <strong>name</strong>.</li>
          <li>Enter the candidate&apos;s <strong>role</strong>.</li>
          <li>Select the candidate&apos;s current <strong>status</strong>.</li>
          <li>Enter the candidate&apos;s <strong>score</strong>, if available.</li>
          <li>Select the appropriate <strong>risk level</strong>, if available.</li>
          <li>Click <strong>Add Candidate</strong>.</li>
          <li>
            Verify that the candidate appears in the
            <strong> Candidate Evaluation</strong> table.
          </li>
        </ol>

        <div className="mt-5 space-y-4">
          <img
            src="/help/add candidates.png"
            alt="Add Candidate form"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/candidate-filled.png"
            alt="Candidate form filled"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/candidate-added.png"
            alt="Candidate added successfully"
            className="w-full rounded-md border border-border"
          />
        </div>
      </section>

      {/* 2. Starting an Interview */}
      <section className="rounded-lg border border-border bg-bg-card p-6">
        <h2 className="text-xl font-semibold text-zinc-50">
          2. Starting an Interview
        </h2>

        <p className="mt-2 text-sm text-muted">
          Use the Interview page to start an interview session for a
          candidate.
        </p>

        <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-zinc-200">
          <li>Open the <strong>Interview</strong> page.</li>
          <li>
            Enter the candidate&apos;s <strong>Candidate ID</strong>.
          </li>
          <li>Click <strong>Start Interview</strong>.</li>
          <li>
            Allow camera and microphone access when requested.
          </li>
          <li>
            During the interview, use the available controls to
            mute/unmute the microphone, pause/resume, or end the interview.
          </li>
          <li>
            Monitor the available interview information and risk indicators
            during the session.
          </li>
        </ol>

        <div className="mt-5 space-y-4">
          <img
            src="/help/interview-start.png"
            alt="Interview start screen"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/interview-active.png"
            alt="Active interview screen"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/interview-risk.png"
            alt="Interview risk information"
            className="w-full rounded-md border border-border"
          />
        </div>
      </section>

      {/* 3. Reviewing Reports */}
      <section className="rounded-lg border border-border bg-bg-card p-6">
        <h2 className="text-xl font-semibold text-zinc-50">
          3. Reviewing Reports
        </h2>

        <p className="mt-2 text-sm text-muted">
          The Analytics page provides interview and hiring insights for
          reviewing candidate and session performance.
        </p>

        <ol className="mt-4 list-decimal space-y-3 pl-6 text-sm text-zinc-200">
          <li>Open the <strong>Analytics</strong> page.</li>
          <li>
            Select a date range such as <strong>All time</strong>,
            <strong> Last 24h</strong>, <strong>Last 7d</strong>, or
            <strong> Last 30d</strong>.
          </li>
          <li>
            Review the session statistics, including total sessions,
            average risk, and high-risk sessions.
          </li>
          <li>Review <strong>Sessions by Status</strong>.</li>
          <li>
            Review the <strong>Failure Breakdown</strong> when required.
          </li>
          <li>
            Review the <strong>Risk Distribution</strong>.
          </li>
          <li>
            Review the <strong>Trend Analysis</strong> for completed and
            failed sessions.
          </li>
          <li>
            Use <strong>Export CSV</strong> when a downloadable candidate
            summary is required.
          </li>
        </ol>

        <div className="mt-5 space-y-4">
          <img
            src="/help/analytics-overview (2).png"
            alt="Analytics overview"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/risk-reports.png"
            alt="Risk reports"
            className="w-full rounded-md border border-border"
          />

          <img
            src="/help/A trend-analysis.png"
            alt="Trend analysis"
            className="w-full rounded-md border border-border"
          />
        </div>
      </section>

      {/* 4. Interview Report */}
      <section className="rounded-lg border border-border bg-bg-card p-6">
        <h2 className="text-xl font-semibold text-zinc-50">
          4. Interview Report Information
        </h2>

        <p className="mt-2 text-sm text-muted">
          A completed interview report can contain the following information:
        </p>

        <ul className="mt-4 list-disc space-y-2 pl-6 text-sm text-zinc-200">
          <li>Candidate information</li>
          <li>Interview start and end time</li>
          <li>Interview duration</li>
          <li>Interview questions and answers</li>
          <li>Overall evaluation</li>
          <li>AI feedback and recommendations</li>
          <li>Risk score and risk classification</li>
          <li>Risk factors</li>
        </ul>

        <div className="mt-5">
          <img
            src="/help/risk-reports.png"
            alt="Interview report and risk report"
            className="w-full rounded-md border border-border"
          />
        </div>
      </section>

      {/* 5. Troubleshooting */}
      <section className="rounded-lg border border-border bg-bg-card p-6">
        <h2 className="text-xl font-semibold text-zinc-50">
          5. Basic Troubleshooting
        </h2>

        <ul className="mt-4 list-disc space-y-2 pl-6 text-sm text-zinc-200">
          <li>
            If candidate information does not appear, refresh the page and
            verify the entered information.
          </li>
          <li>
            If an interview cannot start, verify the Candidate ID and check
            that the application is available.
          </li>
          <li>
            If camera or microphone access is requested, allow the required
            browser permissions.
          </li>
          <li>
            If reports are unavailable, check whether the interview session
            has completed.
          </li>
        </ul>
      </section>
    </div>
  );
}