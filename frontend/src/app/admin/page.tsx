"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getAdminQueue,
  getAdminSession,
  getBoothStats,
  skipQueueUser,
  forceEndSession,
  startMirrorSession,
  advanceQueue,
  AdminQueueEntry,
  AdminSessionInfo,
  BoothStats,
} from "@/lib/api";

const POLL_INTERVAL = 10_000;

export default function AdminPage() {
  const [queue, setQueue] = useState<AdminQueueEntry[]>([]);
  const [session, setSession] = useState<AdminSessionInfo | null>(null);
  const [stats, setStats] = useState<BoothStats | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [q, s, st] = await Promise.all([
        getAdminQueue(),
        getAdminSession(),
        getBoothStats(),
      ]);
      setQueue(q);
      setSession(s);
      setStats(st);
    } catch (err) {
      console.error("[Admin] Refresh failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [refresh]);

  const handleSkip = useCallback(
    async (userId: string) => {
      await skipQueueUser(userId);
      refresh();
    },
    [refresh]
  );

  const handleForceEnd = useCallback(async () => {
    await forceEndSession();
    refresh();
  }, [refresh]);

  const handleStartSession = useCallback(
    async (userId: string) => {
      await startMirrorSession(userId);
      refresh();
    },
    [refresh]
  );

  const handleAdvance = useCallback(async () => {
    await advanceQueue();
    refresh();
  }, [refresh]);

  if (loading) {
    return (
      <main className="min-h-screen bg-zinc-50 flex items-center justify-center">
        <p className="text-zinc-400">Loading admin panel...</p>
      </main>
    );
  }

  const activeEntry = queue.find((q) => q.status === "active");
  const waitingEntries = queue.filter((q) => q.status === "waiting");

  return (
    <main className="min-h-screen bg-zinc-50 p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">Mirrorless Admin</h1>
          <button
            onClick={refresh}
            className="text-sm text-zinc-500 hover:text-zinc-900 underline"
          >
            Refresh
          </button>
        </div>

        {/* Booth Stats */}
        {stats && (
          <div className="grid grid-cols-4 gap-4 mb-8">
            <StatCard label="Users Today" value={stats.total_users_today} />
            <StatCard
              label="Avg Session"
              value={`${Math.round(stats.avg_session_seconds)}s`}
            />
            <StatCard label="Items Shown" value={stats.total_items_shown} />
            <StatCard label="Items Liked" value={stats.total_items_liked} />
          </div>
        )}

        {/* Current Session */}
        <section className="bg-white rounded-xl border border-zinc-200 p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Current Session</h2>
          {session ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{session.name}</p>
                <p className="text-sm text-zinc-500">
                  API calls: {session.api_calls} | Items: {session.items_shown} shown, {session.items_liked} liked
                </p>
              </div>
              <button
                onClick={handleForceEnd}
                className="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-600"
              >
                Force End
              </button>
            </div>
          ) : activeEntry ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">{activeEntry.name}</p>
                <p className="text-sm text-zinc-500">Waiting at mirror (no session started)</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleStartSession(activeEntry.user_id)}
                  className="bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-600"
                >
                  Start Session
                </button>
                <button
                  onClick={() => handleSkip(activeEntry.user_id)}
                  className="bg-zinc-200 text-zinc-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-zinc-300"
                >
                  Skip
                </button>
              </div>
            </div>
          ) : (
            <p className="text-zinc-400">No active session</p>
          )}
        </section>

        {/* Queue */}
        <section className="bg-white rounded-xl border border-zinc-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">
              Queue ({waitingEntries.length} waiting)
            </h2>
            {waitingEntries.length > 0 && !activeEntry && (
              <button
                onClick={handleAdvance}
                className="text-sm text-blue-600 hover:underline"
              >
                Advance Next
              </button>
            )}
          </div>
          {waitingEntries.length === 0 ? (
            <p className="text-zinc-400">Queue is empty</p>
          ) : (
            <div className="divide-y divide-zinc-100">
              {waitingEntries.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between py-3"
                >
                  <div className="flex items-center gap-3">
                    <span className="w-8 h-8 rounded-full bg-zinc-100 flex items-center justify-center text-sm font-medium">
                      {entry.position}
                    </span>
                    <span className="font-medium">{entry.name}</span>
                  </div>
                  <button
                    onClick={() => handleSkip(entry.user_id)}
                    className="text-sm text-red-500 hover:underline"
                  >
                    Skip
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-xl border border-zinc-200 p-4 text-center">
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-xs text-zinc-500 mt-1">{label}</p>
    </div>
  );
}
