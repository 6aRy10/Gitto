'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "./ui/table";
import { Button } from "./ui/button";
import { getAsyncTaskStatus } from '../lib/api';
import { RefreshCw, CheckCircle2, Clock, AlertCircle, Loader } from "lucide-react";

export default function AsyncOperationsView({ taskIds }: { taskIds?: string[] }) {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (taskIds && taskIds.length > 0) {
      loadTasks();
      // Poll for updates
      const interval = setInterval(loadTasks, 2000);
      return () => clearInterval(interval);
    }
  }, [taskIds]);

  const loadTasks = async () => {
    if (!taskIds || taskIds.length === 0) return;
    
    setLoading(true);
    try {
      const results = await Promise.all(
        taskIds.map(id => getAsyncTaskStatus(id).catch(() => null))
      );
      setTasks(results.filter(t => t !== null));
    } catch (e) {
      console.error("Failed to load tasks:", e);
    }
    setLoading(false);
  };

  const statusConfig: Record<string, { icon: any; color: string; bgColor: string }> = {
    pending: { icon: Clock, color: 'text-amber-400', bgColor: 'bg-amber-500/20' },
    running: { icon: Loader, color: 'text-blue-400', bgColor: 'bg-blue-500/20' },
    completed: { icon: CheckCircle2, color: 'text-emerald-400', bgColor: 'bg-emerald-500/20' },
    failed: { icon: AlertCircle, color: 'text-red-400', bgColor: 'bg-red-500/20' }
  };

  if (!taskIds || taskIds.length === 0) {
    return (
      <Card className="rounded-[32px] border-white/10 bg-white/5 p-16 text-center">
        <AlertCircle className="h-12 w-12 text-white/30 mx-auto mb-4" />
        <p className="text-white/60 font-medium">No async tasks to display</p>
      </Card>
    );
  }

  return (
    <div className="space-y-8 mt-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-white">Async Operations</h2>
          <p className="text-sm text-white/40 font-medium mt-1">
            Track long-running task status
          </p>
        </div>
        <Button
          onClick={loadTasks}
          disabled={loading}
          className="bg-white text-[#0A0A0F] hover:bg-white/90 rounded-xl h-10 px-6 text-xs font-bold"
        >
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <Card className="rounded-[32px] border-white/10 bg-white/5 overflow-hidden">
        <CardHeader className="p-8 border-b border-white/10">
          <CardTitle className="text-xl font-black text-white">Task Status</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-white/5">
              <TableRow className="border-white/10">
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Task ID</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Type</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Status</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Created</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Completed</TableHead>
                <TableHead className="text-white/60 font-black uppercase text-[10px] tracking-widest">Result</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {tasks.map((task: any, i: number) => {
                const config = statusConfig[task.status] || statusConfig.pending;
                const Icon = config.icon;
                
                return (
                  <TableRow key={i} className="border-white/10 hover:bg-white/5">
                    <TableCell className="text-white/80 text-xs font-mono">
                      {task.task_id?.substring(0, 8)}...
                    </TableCell>
                    <TableCell className="text-white font-medium capitalize">
                      {task.task_type?.replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className={`h-4 w-4 ${config.color} ${task.status === 'running' ? 'animate-spin' : ''}`} />
                        <span className={`px-2.5 py-1 rounded-lg text-[10px] font-black uppercase ${config.bgColor} ${config.color} border`}>
                          {task.status}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="text-white/60 text-xs">
                      {task.created_at ? new Date(task.created_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="text-white/60 text-xs">
                      {task.completed_at ? new Date(task.completed_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell className="text-white/60 text-xs">
                      {task.error ? (
                        <span className="text-red-400">{task.error.substring(0, 30)}...</span>
                      ) : task.result ? (
                        <span className="text-emerald-400">Success</span>
                      ) : (
                        '-'
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
              {tasks.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-12 text-white/40">
                    No tasks found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}


