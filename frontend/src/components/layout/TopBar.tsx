"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiRequest } from "@/lib/api";
import { NotificationItem } from "@/lib/types";
import {
  Bell,
  ShieldCheck,
  Building,
  LogOut,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  Clock,
  CheckCheck,
  ExternalLink,
} from "lucide-react";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  const [isOpen, setIsOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  const fetchUnreadCount = async () => {
    try {
      const res = await apiRequest<{ unread_count: number }>("/notifications/unread-count");
      setUnreadCount(res.unread_count);
    } catch {
      // silently fail if unauthenticated or network drop
    }
  };

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const res = await apiRequest<{ items: NotificationItem[]; total: number; unread_count: number }>("/notifications?limit=25");
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    fetchUnreadCount();

    // Poll every 15 seconds to pick up live notifications without manual page reload
    const interval = setInterval(() => {
      fetchUnreadCount();
      if (isOpen) {
        fetchNotifications();
      }
    }, 15000);

    return () => clearInterval(interval);
  }, [user, isOpen]);

  // When dropdown opens, fetch latest notifications list
  const toggleNotifications = () => {
    if (!isOpen) {
      fetchNotifications();
    }
    setIsOpen(!isOpen);
  };

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkAsRead = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await apiRequest(`/notifications/${notif.id}/read`, { method: "POST" });
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (err) {
        console.error("Failed to mark notification as read", err);
      }
    }
    if (notif.link) {
      setIsOpen(false);
      router.push(notif.link);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiRequest("/notifications/mark-all-read", { method: "POST" });
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Failed to mark all as read", err);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case "decision":
        return <FileCheck2 className="w-4 h-4 text-emerald-600 shrink-0" />;
      case "info_request":
        return <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />;
      case "review":
        return <Clock className="w-4 h-4 text-blue-500 shrink-0" />;
      case "submission":
        return <CheckCircle2 className="w-4 h-4 text-indigo-500 shrink-0" />;
      default:
        return <Bell className="w-4 h-4 text-slate-500 shrink-0" />;
    }
  };

  const formatTimestamp = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      const diffDays = Math.floor(diffHours / 24);

      if (diffMins < 1) return "Just now";
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  if (!user) return null;

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-xs shrink-0 relative z-30">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 p-0.5 flex items-center justify-center shadow-2xs shrink-0">
          <img
            src="/assets/aicte_logo.png"
            alt="AICTE Logo"
            className="w-full h-full object-contain"
          />
        </div>
        <h1 className="text-base font-bold text-slate-800 tracking-tight flex items-center gap-2">
          <span className="text-[#0A4D2E] font-black tracking-wide">SARATHI</span>
          <span className="text-xs font-medium text-slate-500 hidden sm:inline">| AICTE Regulatory Governance Portal</span>
        </h1>
      </div>

      <div className="flex items-center gap-4">
        {/* Caveat reminder */}
        <div className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 text-[#0A4D2E] text-xs font-medium border border-emerald-200/80">
          <ShieldCheck className="w-3.5 h-3.5 text-[#0A4D2E]" />
          <span>Decision Support Mode &bull; AI Recommends, Official Decides</span>
        </div>

        {/* Institution Badge if applicable */}
        {user.institution_id && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50 text-[#0A4D2E] text-xs font-medium border border-emerald-200">
            <Building className="w-3.5 h-3.5" />
            <span>Institution ID: #{user.institution_id}</span>
          </div>
        )}

        {/* Notifications Popover */}
        <div className="relative" ref={popoverRef}>
          <button
            onClick={toggleNotifications}
            id="notifications-bell-btn"
            className="relative p-2 rounded-full text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors focus:outline-none"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-[10px] font-bold text-white flex items-center justify-center ring-2 ring-white">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </button>

          {isOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden z-50">
              {/* Header */}
              <div className="px-4 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-bold text-slate-800">Notifications</h3>
                  {unreadCount > 0 && (
                    <span className="px-2 py-0.5 text-[11px] font-semibold bg-red-100 text-red-700 rounded-full">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-xs text-[#0A4D2E] hover:text-[#083D24] font-medium flex items-center gap-1"
                  >
                    <CheckCheck className="w-3.5 h-3.5" />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>

              {/* List */}
              <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
                {loading && notifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-400">
                    Loading notifications...
                  </div>
                ) : notifications.length === 0 ? (
                  <div className="p-8 text-center text-xs text-slate-400">
                    <Bell className="w-8 h-8 text-slate-300 mx-auto mb-2 opacity-50" />
                    <p className="font-medium text-slate-500">No notifications yet</p>
                    <p className="text-[11px] mt-0.5">Official decisions and request updates will appear here.</p>
                  </div>
                ) : (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => handleMarkAsRead(notif)}
                      className={`p-3.5 flex items-start gap-3 hover:bg-slate-50 cursor-pointer transition-colors ${
                        !notif.is_read ? "bg-emerald-50/40" : ""
                      }`}
                    >
                      <div className="mt-0.5 p-1.5 rounded-lg bg-white border border-slate-200 shadow-sm">
                        {getCategoryIcon(notif.category)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-1">
                          <p className={`text-xs ${!notif.is_read ? "font-bold text-slate-900" : "font-medium text-slate-700"} truncate`}>
                            {notif.title}
                          </p>
                          <span className="text-[10px] text-slate-400 whitespace-nowrap">
                            {formatTimestamp(notif.created_at)}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-600 mt-0.5 line-clamp-2 leading-relaxed">
                          {notif.message}
                        </p>
                        {notif.link && (
                          <div className="mt-1 flex items-center gap-1 text-[10px] text-[#0A4D2E] font-medium">
                            <span>Open details</span>
                            <ExternalLink className="w-2.5 h-2.5" />
                          </div>
                        )}
                      </div>
                      {!notif.is_read && (
                        <div className="w-2 h-2 rounded-full bg-[#0A4D2E] mt-1.5 shrink-0" title="Unread" />
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User avatar pill & logout */}
        <div className="flex items-center gap-2.5 pl-3 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-[#0A4D2E] text-white font-bold flex items-center justify-center text-xs shadow-inner">
            {user.full_name.charAt(0)}
          </div>
          <div className="text-left hidden md:block">
            <p className="text-xs font-bold text-slate-800 leading-tight">{user.full_name}</p>
            <p className="text-[11px] text-slate-500 capitalize">{user.role}</p>
          </div>
          <button
            onClick={logout}
            title="Sign out of SARATHI Portal"
            className="p-1.5 ml-1 text-slate-400 hover:text-red-500 hover:bg-slate-100 rounded-lg transition-colors flex items-center gap-1"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span className="text-[11px] font-semibold hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
}

