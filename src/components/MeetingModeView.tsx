'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { api } from '../lib/api';
import { 
  CheckCircle2, XCircle, AlertTriangle, Lock, Unlock, 
  FileText, TrendingUp, Users, ArrowRight, Loader2,
  AlertCircle, CheckSquare, Square
} from 'lucide-react';

interface Exception {
  id: number;
  exception_type: string;
  severity: string;
  amount: number;
  status: string;
  assignee: string | null;
  aging_days: number;
  resolution_note: string | null;
}

interface Action {
  id: number;
  action_type: string;
  name: string;
  owner: string;
  expected_impact: number;
  status: string;
  approvals: any[];
}

interface SnapshotStatus {
  snapshot_id: number;
  status: string;
  is_locked: boolean;
  lock_gate_checks: {
    missing_fx_rate: {
      passed: boolean;
      actual_pct: number;
      threshold: number;
      message: string;
    };
    unexplained_cash: {
      passed: boolean;
      actual_pct: number;
      threshold: number;
      message: string;
    };
  };
  can_transition_to_ready: boolean;
  can_transition_to_locked: boolean;
}

interface MeetingModeViewProps {
  snapshotId: number;
  compareId?: number;
}

export default function MeetingModeView({ snapshotId, compareId }: MeetingModeViewProps) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [exceptions, setExceptions] = useState<Exception[]>([]);
  const [actions, setActions] = useState<Action[]>([]);
  const [snapshotStatus, setSnapshotStatus] = useState<SnapshotStatus | null>(null);
  const [variance, setVariance] = useState<any>(null);
  const [reviewedExceptions, setReviewedExceptions] = useState<Set<number>>(new Set());
  const [approvedActions, setApprovedActions] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [snapshotId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [exceptionsRes, actionsRes, statusRes, varianceRes] = await Promise.all([
        api.get(`/snapshots/${snapshotId}/exceptions`),
        api.get(`/snapshots/${snapshotId}/actions`),
        api.get(`/snapshots/${snapshotId}/status`),
        compareId ? api.get(`/snapshots/${snapshotId}/variance?compare_id=${compareId}`).catch(() => null) : Promise.resolve(null)
      ]);

      setExceptions(exceptionsRes.data || []);
      setActions(actionsRes.data || []);
      setSnapshotStatus(statusRes.data);
      setVariance(varianceRes?.data || null);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load meeting mode data');
    } finally {
      setLoading(false);
    }
  };

  const handleReviewException = (exceptionId: number) => {
    setReviewedExceptions(new Set([...reviewedExceptions, exceptionId]));
  };

  const handleApproveAction = async (actionId: number) => {
    try {
      // In a real implementation, this would call an approval endpoint
      setApprovedActions(new Set([...approvedActions, actionId]));
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to approve action');
    }
  };

  const handleMarkReadyForReview = async () => {
    setLoading(true);
    try {
      await api.post(`/snapshots/${snapshotId}/ready-for-review`, { user_id: 'current_user' });
      await loadData();
      setStep(2);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to mark ready for review');
    } finally {
      setLoading(false);
    }
  };

  const handleLockSnapshot = async (force: boolean = false) => {
    setLoading(true);
    try {
      await api.post(`/snapshots/${snapshotId}/lock`, {
        user_id: 'current_user',
        lock_type: 'Meeting',
        force
      });
      await loadData();
      setStep(5);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to lock snapshot');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateWeeklyPack = async () => {
    setLoading(true);
    try {
      // Generate weekly pack
      const pack = await api.post(`/snapshots/${snapshotId}/meeting-mode`);
      // In a real implementation, this would download or display the pack
      alert('Weekly pack generated successfully!');
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to generate weekly pack');
    } finally {
      setLoading(false);
    }
  };

  const canProceedToStep2 = exceptions.length === 0 || exceptions.every(e => reviewedExceptions.has(e.id));
  const canProceedToStep3 = variance !== null;
  const canProceedToStep4 = actions.length === 0 || actions.every(a => 
    a.status === 'approved' || approvedActions.has(a.id)
  );
  const canProceedToStep5 = snapshotStatus?.can_transition_to_locked && 
    snapshotStatus?.lock_gate_checks?.missing_fx_rate?.passed &&
    snapshotStatus?.lock_gate_checks?.unexplained_cash?.passed;

  if (loading && !snapshotStatus) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Meeting Mode</h1>
        <div className="flex gap-2">
          <span className="text-sm text-gray-500">Snapshot {snapshotId}</span>
          {snapshotStatus?.is_locked && (
            <span className="flex items-center gap-1 text-sm text-green-600">
              <Lock className="w-4 h-4" />
              Locked
            </span>
          )}
        </div>
      </div>

      {error && (
        <Card className="border-red-500 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-700">
              <AlertCircle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step Progress */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            {[1, 2, 3, 4, 5].map((s) => (
              <div key={s} className="flex items-center">
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 ${
                  step >= s ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 text-gray-400'
                }`}>
                  {step > s ? <CheckCircle2 className="w-6 h-6" /> : s}
                </div>
                {s < 5 && (
                  <div className={`w-20 h-1 ${step > s ? 'bg-blue-600' : 'bg-gray-300'}`} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>Review Exceptions</span>
            <span>Variance Diff</span>
            <span>Approve Actions</span>
            <span>Lock Snapshot</span>
            <span>Generate Pack</span>
          </div>
        </CardContent>
      </Card>

      {/* Step 1: Review Exceptions */}
      {step === 1 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 1: Review Exceptions</CardTitle>
            <CardDescription>
              Review and resolve all exceptions before proceeding
            </CardDescription>
          </CardHeader>
          <CardContent>
            {exceptions.length === 0 ? (
              <div className="flex items-center gap-2 text-green-600 py-4">
                <CheckCircle2 className="w-5 h-5" />
                <span>No exceptions to review</span>
              </div>
            ) : (
              <div className="space-y-4">
                {exceptions.map((exception) => (
                  <div
                    key={exception.id}
                    className={`p-4 border rounded-lg ${
                      reviewedExceptions.has(exception.id) ? 'bg-green-50 border-green-200' : 'bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            exception.severity === 'critical' ? 'bg-red-100 text-red-700' :
                            exception.severity === 'error' ? 'bg-orange-100 text-orange-700' :
                            exception.severity === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {exception.severity}
                          </span>
                          <span className="font-semibold">{exception.exception_type}</span>
                        </div>
                        <div className="mt-2 text-sm text-gray-600">
                          Amount: €{exception.amount?.toLocaleString() || 'N/A'} | 
                          Aging: {exception.aging_days} days | 
                          Assignee: {exception.assignee || 'Unassigned'}
                        </div>
                        {exception.resolution_note && (
                          <div className="mt-2 text-sm text-gray-500">
                            Resolution: {exception.resolution_note}
                          </div>
                        )}
                      </div>
                      <Button
                        onClick={() => handleReviewException(exception.id)}
                        variant={reviewedExceptions.has(exception.id) ? "outline" : "default"}
                        size="sm"
                      >
                        {reviewedExceptions.has(exception.id) ? (
                          <>
                            <CheckSquare className="w-4 h-4 mr-1" />
                            Reviewed
                          </>
                        ) : (
                          <>
                            <Square className="w-4 h-4 mr-1" />
                            Mark Reviewed
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-6 flex justify-end">
              <Button
                onClick={handleMarkReadyForReview}
                disabled={!canProceedToStep2 || loading}
              >
                Mark Ready for Review
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 2: Variance Diff */}
      {step === 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 2: Review Variance Diff</CardTitle>
            <CardDescription>
              Compare current snapshot with previous snapshot
            </CardDescription>
          </CardHeader>
          <CardContent>
            {variance ? (
              <div className="space-y-4">
                <div className="p-4 bg-blue-50 rounded-lg">
                  <h3 className="font-semibold mb-2">Variance Summary</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Total Variance</div>
                      <div className="text-2xl font-bold">
                        €{variance.total_variance?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Inflow Variance</div>
                      <div className="text-2xl font-bold text-green-600">
                        €{variance.inflow_variance?.toLocaleString() || '0'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Outflow Variance</div>
                      <div className="text-2xl font-bold text-red-600">
                        €{variance.outflow_variance?.toLocaleString() || '0'}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                No comparison snapshot provided
              </div>
            )}
            <div className="mt-6 flex justify-between">
              <Button onClick={() => setStep(1)} variant="outline">
                Back
              </Button>
              <Button
                onClick={() => setStep(3)}
                disabled={!canProceedToStep3}
              >
                Proceed to Actions
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Approve Actions */}
      {step === 3 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 3: Approve Actions</CardTitle>
            <CardDescription>
              Review and approve all actions before locking snapshot
            </CardDescription>
          </CardHeader>
          <CardContent>
            {actions.length === 0 ? (
              <div className="flex items-center gap-2 text-green-600 py-4">
                <CheckCircle2 className="w-5 h-5" />
                <span>No actions to approve</span>
              </div>
            ) : (
              <div className="space-y-4">
                {actions.map((action) => (
                  <div
                    key={action.id}
                    className={`p-4 border rounded-lg ${
                      approvedActions.has(action.id) || action.status === 'approved' 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-white'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-semibold">{action.name}</div>
                        <div className="text-sm text-gray-600 mt-1">
                          Type: {action.action_type} | 
                          Owner: {action.owner} | 
                          Expected Impact: €{action.expected_impact?.toLocaleString() || '0'}
                        </div>
                        <div className="mt-2">
                          <span className={`px-2 py-1 rounded text-xs ${
                            action.status === 'approved' ? 'bg-green-100 text-green-700' :
                            action.status === 'pending_approval' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {action.status}
                          </span>
                        </div>
                      </div>
                      {action.status !== 'approved' && (
                        <Button
                          onClick={() => handleApproveAction(action.id)}
                          variant={approvedActions.has(action.id) ? "outline" : "default"}
                          size="sm"
                        >
                          {approvedActions.has(action.id) ? 'Approved' : 'Approve'}
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-6 flex justify-between">
              <Button onClick={() => setStep(2)} variant="outline">
                Back
              </Button>
              <Button
                onClick={() => setStep(4)}
                disabled={!canProceedToStep4 || loading}
              >
                Proceed to Lock
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Lock Snapshot */}
      {step === 4 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 4: Lock Snapshot</CardTitle>
            <CardDescription>
              Lock snapshot after all gates pass
            </CardDescription>
          </CardHeader>
          <CardContent>
            {snapshotStatus && (
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold mb-4">Lock Gate Checks</h3>
                  <div className="space-y-3">
                    <div className={`flex items-center justify-between p-3 rounded ${
                      snapshotStatus.lock_gate_checks.missing_fx_rate.passed 
                        ? 'bg-green-50' 
                        : 'bg-red-50'
                    }`}>
                      <div>
                        <div className="font-medium">Missing FX Rate</div>
                        <div className="text-sm text-gray-600">
                          {snapshotStatus.lock_gate_checks.missing_fx_rate.message}
                        </div>
                      </div>
                      {snapshotStatus.lock_gate_checks.missing_fx_rate.passed ? (
                        <CheckCircle2 className="w-6 h-6 text-green-600" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-600" />
                      )}
                    </div>
                    <div className={`flex items-center justify-between p-3 rounded ${
                      snapshotStatus.lock_gate_checks.unexplained_cash.passed 
                        ? 'bg-green-50' 
                        : 'bg-red-50'
                    }`}>
                      <div>
                        <div className="font-medium">Unexplained Cash</div>
                        <div className="text-sm text-gray-600">
                          {snapshotStatus.lock_gate_checks.unexplained_cash.message}
                        </div>
                      </div>
                      {snapshotStatus.lock_gate_checks.unexplained_cash.passed ? (
                        <CheckCircle2 className="w-6 h-6 text-green-600" />
                      ) : (
                        <XCircle className="w-6 h-6 text-red-600" />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
            <div className="mt-6 flex justify-between">
              <Button onClick={() => setStep(3)} variant="outline">
                Back
              </Button>
              <div className="flex gap-2">
                {!canProceedToStep5 && (
                  <Button
                    onClick={() => handleLockSnapshot(true)}
                    variant="outline"
                    disabled={loading}
                  >
                    Force Lock
                  </Button>
                )}
                <Button
                  onClick={() => handleLockSnapshot(false)}
                  disabled={!canProceedToStep5 || loading}
                >
                  <Lock className="w-4 h-4 mr-2" />
                  Lock Snapshot
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 5: Generate Weekly Pack */}
      {step === 5 && (
        <Card>
          <CardHeader>
            <CardTitle>Step 5: Generate Weekly Pack</CardTitle>
            <CardDescription>
              Generate weekly cash pack for meeting
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
              <p className="text-gray-600 mb-6">
                Snapshot is locked and ready for weekly pack generation
              </p>
              <Button
                onClick={handleGenerateWeeklyPack}
                disabled={loading}
                size="lg"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <FileText className="w-4 h-4 mr-2" />
                    Generate Weekly Pack
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


