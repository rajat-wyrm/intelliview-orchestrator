export default function HelpPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">HR User Manual</h1>

      <p className="mb-6">
        Welcome to the AI-IntelliView HR User Manual.
      </p>

      <h2 className="text-xl font-semibold mb-2">Guide</h2>

      <ul className="list-disc pl-6 space-y-2">
        <li>Adding Candidates</li>
        <li>Scheduling Interviews</li>
        <li>Reviewing Reports</li>
      </ul>

      <p className="mt-6 text-gray-400">
        This guide is currently under development.
      </p>
    </div>
  );
}