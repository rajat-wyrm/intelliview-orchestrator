"use client";

import { useState, useEffect, useMemo } from "react";
import useSWR from "swr";
import { api, endpoints } from "@/lib/api";
import {
  Calendar as CalendarIcon,
  Clock,
  User,
  Mail,
  Plus,
  CheckCircle2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Send,
  CalendarCheck,
  FileText,
  Filter,
} from "lucide-react";

import Card from "@/components/Card";
import Button from "@/components/Button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
} from "@/components/Dialog";
import { Badge } from "@/components/Badge";
import { Skeleton } from "@/components/States";
import { Table, Thead, Tbody, Tr, Th, Td } from "@/components/ui";

export default function SchedulePage() {
  const { data: candidateData, isLoading: loadingCandidates } = useSWR("candidates", endpoints.candidates);
  const { data: scheduleData, mutate: refreshSchedules, isLoading: loadingSchedules } = useSWR("schedule", () => endpoints.schedule());

  // Form State
  const [selectedCandidateId, setSelectedCandidateId] = useState("");
  const [interviewerId, setInterviewerId] = useState("HR Tech Team");
  
  // Default to tomorrow 10:00 AM local ISO format
  const getTomorrowDefault = () => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    d.setHours(10, 0, 0, 0);
    return d.toISOString().slice(0, 16);
  };
  const [scheduledAt, setScheduledAt] = useState(getTomorrowDefault());
  const [notes, setNotes] = useState("Technical Evaluation Round");
  const [sendEmail, setSendEmail] = useState(true);

  // UI state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [notification, setNotification] = useState(null);
  const [currentMonthDate, setCurrentMonthDate] = useState(new Date());
  const [statusFilter, setStatusFilter] = useState("all");
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [scheduleToCancel, setScheduleToCancel] = useState(null);

  const [rescheduleDialogOpen, setRescheduleDialogOpen] = useState(false);
  const [scheduleToReschedule, setScheduleToReschedule] = useState(null);
  const [rescheduleAt, setRescheduleAt] = useState("");
  const [isUpdatingSchedule, setIsUpdatingSchedule] = useState(false);

  const sampleCandidates = [
    { id: "cand-101", name: "Jyoshna Sankarapu (Candidate)", email: "jyoshna@example.com" },
    { id: "cand-102", name: "Alice Johnson", email: "alice.johnson@example.com" },
    { id: "cand-103", name: "Bob Smith", email: "bob.smith@example.com" },
    { id: "cand-104", name: "Carol Danvers", email: "carol.danvers@example.com" },
    { id: "cand-105", name: "David Miller", email: "david.miller@example.com" },
  ];

  const candidates = (candidateData?.candidates && candidateData.candidates.length > 0)
    ? candidateData.candidates
    : (Array.isArray(candidateData) && candidateData.length > 0)
      ? candidateData
      : sampleCandidates;

  const rawSchedules = scheduleData?.schedules || [];

  // Filtered schedules
  const schedules = useMemo(() => {
    if (statusFilter === "all") return rawSchedules;
    return rawSchedules.filter((s) => s.status === statusFilter);
  }, [rawSchedules, statusFilter]);

  // Handle Form Submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedCandidateId) {
      setNotification({ type: "error", message: "Please select a candidate." });
      return;
    }

    setIsSubmitting(true);
    setNotification(null);

    try {
      const payload = {
        candidate_id: selectedCandidateId,
        interviewer_id: interviewerId,
        scheduled_at: new Date(scheduledAt).toISOString(),
        notes: notes,
        send_email: sendEmail,
      };      
      const data = await endpoints.createSchedule(payload);
      setNotification({
        type: "success",
        message: `Interview scheduled successfully! ${
          data.email_notification?.sent
            ? "📩 Confirmation email delivered to candidate."
            : `⚠️ ${data.email_notification?.detail || "Email sending skipped."}`
        }`,
      });

      // Refresh list
      refreshSchedules();
      setNotes("");
    } catch (err) {
      setNotification({ type: "error", message: err.message });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Status Change Handler
  const handleStatusUpdate = async (scheduleId, newStatus) => {
    try {
      await endpoints.updateSchedule(scheduleId, { status: newStatus });
      refreshSchedules();
    } catch (err) {
      console.error("Failed to update status", err);
      try {
        const res = await fetch(`/api/schedule/${scheduleId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: newStatus }),
        });
        const data = await res.json();
        if (!res.ok) {
          throw new Error(data.detail || "Failed to update schedule.");
        }
        setNotification({
          type: "success",
          message: `Interview marked as ${newStatus}.`,
        });

        await refreshSchedules();
      } catch (err) {
        setNotification({
          type: "error",
          message: err.message || "Failed to update schedule.",
        });
      }
    }
  };

  const openRescheduleDialog = (schedule) => {
    setScheduleToReschedule(schedule);

    const date = new Date(schedule.scheduled_at);

    const localDateTime = new Date(
      date.getTime() - date.getTimezoneOffset() * 60000
    )
      .toISOString()
      .slice(0, 16);

    setRescheduleAt(localDateTime);
    setRescheduleDialogOpen(true);
  };

  const handleReschedule = async () => {
    if (!scheduleToReschedule || !rescheduleAt) {
      return;
    }

    setIsUpdatingSchedule(true);

    try {
      const res = await fetch(
        `/api/schedule/${scheduleToReschedule.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            schedule_id: scheduleToReschedule.id,
            status: "rescheduled",
            new_scheduled_at: new Date(rescheduleAt).toISOString(),
            scheduled_at: new Date(rescheduleAt).toISOString(),
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail || "Failed to reschedule interview."
        );
      }

      setNotification({
        type: "success",
        message: "Interview rescheduled successfully.",
      });

      setRescheduleDialogOpen(false);
      setScheduleToReschedule(null);
      setRescheduleAt("");

      await refreshSchedules();
    } catch (err) {
      setNotification({
        type: "error",
        message: err.message || "Failed to reschedule interview.",
      });
    } finally {
      setIsUpdatingSchedule(false);
    }
  };

  const handleCancelConfirmed = async () => {
    if (!scheduleToCancel) {
      return;
    }

    setIsUpdatingSchedule(true);

    try {
      const res = await fetch(
        `/api/schedule/${scheduleToCancel.id}`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            schedule_id: scheduleToCancel.id,
            status: "cancelled",
          }),
        }
      );

      const data = await res.json();

      if (!res.ok) {
        throw new Error(
          data.detail || "Failed to cancel interview."
        );
      }

      setNotification({
        type: "success",
        message: "Interview cancelled successfully.",
      });

      setCancelDialogOpen(false);
      setScheduleToCancel(null);

      await refreshSchedules();
    } catch (err) {
      setNotification({
        type: "error",
        message: err.message || "Failed to cancel interview.",
      });
    } finally {
      setIsUpdatingSchedule(false);
    }
  };

  // Calendar Helper Functions
  const year = currentMonthDate.getFullYear();
  const month = currentMonthDate.getMonth();

  const calendarDays = useMemo(() => {
    const firstDayOfMonth = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    const days = [];
    for (let i = 0; i < firstDayOfMonth; i++) {
      days.push(null);
    }
    for (let d = 1; d <= daysInMonth; d++) {
      days.push(new Date(year, month, d));
    }
    return days;
  }, [year, month]);

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];

  return (
    <div className="space-y-6 animate-fade-in p-2 md:p-6 text-zinc-100">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <CalendarIcon className="text-indigo-400" size={24} />
            Interview Scheduling System
          </h1>
          <p className="text-sm text-zinc-400 mt-1">
            Schedule candidate interviews in advance with SMTP email confirmation.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Send size={12} /> SMTP Email Active
          </span>
        </div>
      </div>

      {/* Notification Toast Banner */}
      {notification && (
        <div
          className={`p-4 rounded-lg flex items-start gap-3 border transition-all ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-300"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 size={20} className="shrink-0 mt-0.5" />
          ) : (
            <AlertCircle size={20} className="shrink-0 mt-0.5" />
          )}
          <div className="text-sm font-medium flex-1">{notification.message}</div>
          <button
            onClick={() => setNotification(null)}
            className="text-xs opacity-70 hover:opacity-100 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Grid Layout: Schedule Form + Calendar View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: HR Schedule Form */}
        <div className="lg:col-span-5 space-y-4">
          <div className="bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-xl p-5 shadow-xl">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <Plus className="text-indigo-400" size={18} /> Schedule New Interview
            </h2>

            <form onSubmit={handleSubmit} className="space-y-4 text-sm">
              {/* Candidate Picker */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Select Candidate <span className="text-rose-400">*</span>
                </label>
                {loadingCandidates ? (
                  <Skeleton className="h-10 w-full rounded-md" />
                ) : (
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => setSelectedCandidateId(e.target.value)}
                    required
                    className="w-full bg-zinc-800/90 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">-- Choose Candidate --</option>
                    {candidates.map((c) => (
                      <option key={c.candidate_id} value={c.candidate_id}>
                        {c.name} ({c.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Date & Time Picker */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Interview Date & Time <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="datetime-local"
                    value={scheduledAt}
                    min={new Date().toISOString().slice(0, 16)}
                    onChange={(e) => setScheduledAt(e.target.value)}
                    required
                    className="w-full bg-zinc-800/90 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />

                </div>
              </div>

              {/* Interviewer */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Assigned Interviewer <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={interviewerId}
                  onChange={(e) => setInterviewerId(e.target.value)}
                  placeholder="e.g. HR Manager / Lead Engineer"
                  required
                  className="w-full bg-zinc-800/90 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">
                  Notes / Agenda
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Additional details or evaluation context..."
                  className="w-full bg-zinc-800/90 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* SMTP Checkbox */}
              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="sendEmail"
                  checked={sendEmail}
                  onChange={(e) => setSendEmail(e.target.checked)}
                  className="rounded border-zinc-700 bg-zinc-800 text-indigo-500 focus:ring-indigo-500 h-4 w-4"
                />
                <label htmlFor="sendEmail" className="text-xs text-zinc-300 cursor-pointer">
                  Send confirmation email via <code className="text-indigo-400">smtplib</code>
                </label>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 rounded-lg flex items-center justify-center gap-2"
                >
                  {isSubmitting ? (
                    "Scheduling..."
                  ) : (
                    <>
                      <CalendarCheck size={16} /> Confirm & Schedule Interview
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>

        {/* Right Column: Calendar Grid View */}
        <div className="lg:col-span-7 space-y-4">
          <div className="bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-xl p-5 shadow-xl">
            {/* Calendar Controls */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-white">
                {monthNames[month]} {year}
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentMonthDate(new Date(year, month - 1, 1))}
                  className="p-1.5 rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  onClick={() => setCurrentMonthDate(new Date())}
                  className="px-2.5 py-1 text-xs rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                >
                  Today
                </button>
                <button
                  onClick={() => setCurrentMonthDate(new Date(year, month + 1, 1))}
                  className="p-1.5 rounded-md border border-zinc-700 bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>

            {/* Calendar Header Days */}
            <div className="grid grid-cols-7 gap-1 text-center text-xs font-semibold text-zinc-400 mb-2">
              <div>Sun</div>
              <div>Mon</div>
              <div>Tue</div>
              <div>Wed</div>
              <div>Thu</div>
              <div>Fri</div>
              <div>Sat</div>
            </div>

            {/* Calendar Grid */}
            <div className="grid grid-cols-7 gap-1 text-xs">
              {calendarDays.map((day, idx) => {
                if (!day) {
                  return <div key={`empty-${idx}`} className="h-16 rounded-md bg-zinc-950/40" />;
                }

                const isToday =
                  day.toDateString() === new Date().toDateString();

                // Find matching schedules for this day
                const daySchedules = rawSchedules.filter((s) => {
                  const sDate = new Date(s.scheduled_at);
                  return sDate.toDateString() === day.toDateString();
                });

                return (
                  <div
                    key={day.toISOString()}
                    className={`h-16 p-1 rounded-md border text-left flex flex-col justify-between transition-colors ${
                      isToday
                        ? "border-indigo-500/60 bg-indigo-950/20"
                        : "border-zinc-800/80 bg-zinc-950/60 hover:bg-zinc-800/40"
                    }`}
                  >
                    <div className="flex justify-between items-center">
                      <span
                        className={`font-semibold text-[11px] ${
                          isToday ? "text-indigo-400" : "text-zinc-400"
                        }`}
                      >
                        {day.getDate()}
                      </span>
                      {daySchedules.length > 0 && (
                        <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-pulse" />
                      )}
                    </div>

                    <div className="space-y-0.5 overflow-hidden">
                      {daySchedules.slice(0, 2).map((s) => (
                        <div
                          key={s.id}
                          className="truncate text-[10px] px-1 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-medium"
                          title={`${s.candidate_name} with ${s.interviewer_id}`}
                        >
                          {s.candidate_name}
                        </div>
                      ))}
                      {daySchedules.length > 2 && (
                        <div className="text-[9px] text-zinc-500 pl-0.5">
                          +{daySchedules.length - 2} more
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Scheduled Interviews Table */}
      <div className="bg-zinc-900/80 backdrop-blur-md border border-zinc-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Clock className="text-indigo-400" size={18} /> All Scheduled Interviews
          </h2>

          {/* Filter Bar */}
          <div className="flex items-center gap-2 text-xs">
            <Filter size={14} className="text-zinc-400" />
            <span className="text-zinc-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-zinc-800 border border-zinc-700 rounded px-2.5 py-1 text-zinc-200 focus:outline-none"
            >
              <option value="all">All Statuses</option>
              <option value="scheduled">Scheduled</option>
              <option value="rescheduled">Rescheduled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {loadingSchedules ? (
          <div className="space-y-2 py-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : schedules.length === 0 ? (
          <div className="py-8 text-center text-zinc-500 text-sm">
            No interviews scheduled yet. Use the form above to schedule one!
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <Thead>
                <Tr>
                  <Th>Candidate</Th>
                  <Th>Scheduled Date & Time</Th>
                  <Th>Interviewer</Th>
                  <Th>Status</Th>
                  <Th>Notes</Th>
                  <Th>Actions</Th>
                </Tr>
              </Thead>
              <Tbody>
                {schedules.map((s) => {
                  const sDate = new Date(s.scheduled_at);
                  const formattedDate = sDate.toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  });
                  const formattedTime = sDate.toLocaleTimeString("en-US", {
                    hour: "2-digit",
                    minute: "2-digit",
                  });

                  return (
                    <Tr key={s.id}>
                      <Td>
                        <div className="font-medium text-zinc-100">{s.candidate_name}</div>
                        <div className="text-xs text-zinc-400">{s.candidate_email}</div>
                      </Td>
                      <Td>
                        <div className="text-indigo-300 font-medium">{formattedDate}</div>
                        <div className="text-xs text-zinc-400">{formattedTime}</div>
                      </Td>
                      <Td className="text-zinc-300">{s.interviewer_id}</Td>
                      <Td>
                        <Badge
                          variant={
                            s.status === "completed"
                              ? "success"
                              : s.status === "cancelled"
                              ? "danger"
                              : s.status === "rescheduled"
                              ? "accent"
                              : "accent"
                          }
                        >
                          {s.status}
                        </Badge>
                      </Td>
                      <Td className="text-xs text-zinc-400 max-w-xs truncate">
                        {s.notes || "—"}
                      </Td>
                      <Td>
                        <div className="flex items-center gap-1.5">
                          {(s.status === "scheduled" || s.status === "rescheduled") && (
                            <>
                              <button
                                onClick={() => openRescheduleDialog(s)}
                                className="px-2 py-1 text-[11px] rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 hover:bg-indigo-500/20"
                              >
                                Reschedule
                              </button>
                              <button
                                onClick={() => handleStatusUpdate(s.id, "completed")}
                                className="px-2 py-1 text-[11px] rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                              >
                                Complete
                              </button>
                              <button
                                onClick={() => {
                                  setScheduleToCancel(s);
                                  setCancelDialogOpen(true);
                                }}
                                className="px-2 py-1 text-[11px] rounded bg-rose-500/10 text-rose-400 border border-rose-500/30 hover:bg-rose-500/20"
                              >
                                Cancel
                              </button>
                            </>
                          )}
                        </div>
                      </Td>
                    </Tr>
                  );
                })}
              </Tbody>
            </Table>
          </div>
        )}
      </div>

      {/* Cancel Dialog */}
      <Dialog
        open={cancelDialogOpen}
        onOpenChange={(open) => {
          setCancelDialogOpen(open);

          if (!open) {
            setScheduleToCancel(null);
          }
        }}
      >
        <DialogContent className="max-w-md p-6">
          <DialogTitle>
            Cancel Interview
          </DialogTitle>

          <div className="mt-4 space-y-4">
            <p className="text-sm text-zinc-400">
              Are you sure you want to cancel this interview?
            </p>

            {scheduleToCancel && (
              <div className="rounded-lg border border-zinc-700 bg-zinc-800/60 p-4 space-y-2">
                <div className="text-sm font-medium text-zinc-100">
                  {scheduleToCancel.candidate_name}
                </div>

                <div className="text-xs text-zinc-400">
                  {scheduleToCancel.candidate_email}
                </div>

                <div className="text-xs text-zinc-400">
                  Interviewer:{" "}
                  <span className="text-zinc-200">
                    {scheduleToCancel.interviewer_id}
                  </span>
                </div>

                <div className="text-xs text-zinc-400">
                  Scheduled:{" "}
                  <span className="text-zinc-200">
                    {new Date(
                      scheduleToCancel.scheduled_at
                    ).toLocaleString()}
                  </span>
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setCancelDialogOpen(false);
                  setScheduleToCancel(null);
                }}
                disabled={isUpdatingSchedule}
                className="px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50"
              >
                Keep Interview
              </button>

              <button
                type="button"
                onClick={handleCancelConfirmed}
                disabled={isUpdatingSchedule}
                className="px-3 py-2 text-sm rounded-lg bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50"
              >
                {isUpdatingSchedule ? "Cancelling..." : "Yes, Cancel Interview"}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reschedule Dialog */}
      <Dialog
        open={rescheduleDialogOpen}
        onOpenChange={(open) => {
          setRescheduleDialogOpen(open);

          if (!open) {
            setScheduleToReschedule(null);
            setRescheduleAt("");
          }
        }}
      >
        <DialogContent className="max-w-md p-6">
          <DialogTitle>
            Reschedule Interview
          </DialogTitle>

          <div className="mt-4 space-y-4">
            {scheduleToReschedule && (
              <div className="rounded-lg border border-zinc-700 bg-zinc-800/60 p-4 space-y-2">
                <div className="text-sm font-medium text-zinc-100">
                  {scheduleToReschedule.candidate_name}
                </div>

                <div className="text-xs text-zinc-400">
                  Interviewer:{" "}
                  <span className="text-zinc-200">
                    {scheduleToReschedule.interviewer_id}
                  </span>
                </div>

                <div className="text-xs text-zinc-400">
                  Current time:{" "}
                  <span className="text-zinc-200">
                    {new Date(
                      scheduleToReschedule.scheduled_at
                    ).toLocaleString()}
                  </span>
                </div>
              </div>
            )}

            <div>
              <label
                htmlFor="rescheduleAt"
                className="block text-xs font-medium text-zinc-400 mb-1"
              >
                New Interview Date & Time
              </label>

              <input
                id="rescheduleAt"
                type="datetime-local"
                value={rescheduleAt}
                min={new Date().toISOString().slice(0, 16)}
                onChange={(e) => setRescheduleAt(e.target.value)}
                disabled={isUpdatingSchedule}
                required
                className="w-full bg-zinc-800/90 border border-zinc-700 rounded-lg px-3 py-2 text-zinc-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setRescheduleDialogOpen(false);
                  setScheduleToReschedule(null);
                  setRescheduleAt("");
                }}
                disabled={isUpdatingSchedule}
                className="px-3 py-2 text-sm rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-300 hover:bg-zinc-700 disabled:opacity-50"
              >
                Keep Current Time
              </button>

              <button
                type="button"
                onClick={handleReschedule}
                disabled={isUpdatingSchedule || !rescheduleAt}
                className="px-3 py-2 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {isUpdatingSchedule
                  ? "Rescheduling..."
                  : "Confirm Reschedule"}
              </button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
