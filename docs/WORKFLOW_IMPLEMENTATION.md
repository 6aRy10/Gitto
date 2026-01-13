# First-Class Workflow Objects Implementation

## Overview

Implemented first-class workflow objects and Meeting Mode UI with forced workflow progression.

## Components

### 1. Workflow Models (`backend/workflow_models.py`)

#### Exception
- **Fields**: type, severity, amount, status, assignee, aging, resolution_note
- **Status Flow**: OPEN -> ASSIGNED -> IN_REVIEW -> (RESOLVED | WONT_FIX)
- **Severity Levels**: info, warning, error, critical
- **Aging**: Automatically calculated days since creation

#### Scenario
- **Fields**: branch from base snapshot, actions, approval workflow
- **Status Flow**: DRAFT -> PENDING_APPROVAL -> (APPROVED | REJECTED) -> ACTIVE
- **Branch Name**: Git-like branch naming for scenario tracking
- **Approval**: Required approval before activation

#### Action
- **Fields**: owner, expected impact, status transitions, approvals
- **Status Flow**: DRAFT -> PENDING_APPROVAL -> APPROVED -> IN_PROGRESS -> COMPLETED
- **Status Transitions**: Full audit trail of status changes
- **Approvals**: Multi-approver support with approval chain
- **Impact Tracking**: Expected vs realized impact

### 2. Snapshot State Machine (`backend/snapshot_state_machine.py`)

**State Transitions**:
- `DRAFT` -> `READY_FOR_REVIEW` -> `LOCKED`

**Lock Gates**:
- **Missing FX Rate Threshold**: % of invoices missing FX rates must be below threshold (default: 5%)
- **Unexplained Cash Threshold**: % of cash unexplained must be below threshold (default: 5%)

**Features**:
- Gate checks performed before locking
- Force lock option (bypasses gates)
- Gate check results stored in snapshot

### 3. Meeting Mode UI (`src/components/MeetingModeView.tsx`)

**Forced Workflow Steps**:
1. **Review Exceptions**: Must review all exceptions before proceeding
2. **Variance Diff**: Review variance comparison with previous snapshot
3. **Approve Actions**: Approve all actions before locking
4. **Lock Snapshot**: Lock snapshot after gates pass
5. **Generate Weekly Pack**: Generate weekly cash pack

**Features**:
- Step-by-step progression (cannot skip steps)
- Visual progress indicator
- Gate check visualization
- Force lock option (with warnings)
- Error handling and validation

## API Endpoints

### Snapshot State Machine
- `POST /snapshots/{snapshot_id}/ready-for-review` - Mark ready for review
- `POST /snapshots/{snapshot_id}/lock` - Lock snapshot with gates
- `GET /snapshots/{snapshot_id}/status` - Get status and gate checks

### Workflow Objects
- `GET /snapshots/{snapshot_id}/exceptions` - Get exceptions
- `GET /snapshots/{snapshot_id}/scenarios` - Get scenarios
- `GET /snapshots/{snapshot_id}/actions` - Get actions

## Database Schema Changes

### Snapshot Model
Added fields:
- `status`: State machine status (DRAFT, READY_FOR_REVIEW, LOCKED)
- `ready_for_review_at`: Timestamp when marked ready
- `ready_for_review_by`: User who marked ready
- `locked_at`: Timestamp when locked
- `locked_by`: User who locked
- `missing_fx_threshold`: Threshold for missing FX gate (default: 5.0)
- `unexplained_cash_threshold`: Threshold for unexplained cash gate (default: 5.0)
- `lock_gate_checks`: JSON storing gate check results

### New Tables
- `workflow_exceptions`: Exception objects
- `workflow_scenarios`: Scenario objects (branches)
- `workflow_actions`: Action objects

## Usage

### Meeting Mode Workflow

1. **Start Meeting Mode**:
   ```typescript
   <MeetingModeView snapshotId={123} compareId={122} />
   ```

2. **Workflow Progression**:
   - Step 1: Review all exceptions (mark as reviewed)
   - Step 2: Review variance diff (if comparison snapshot provided)
   - Step 3: Approve all actions
   - Step 4: Lock snapshot (gates must pass)
   - Step 5: Generate weekly pack

3. **Lock Gates**:
   - Missing FX rate: Must be below threshold
   - Unexplained cash: Must be below threshold
   - Force lock available (bypasses gates with warning)

### State Machine Usage

```python
from snapshot_state_machine import SnapshotStateMachine

state_machine = SnapshotStateMachine(db)

# Mark ready for review
state_machine.mark_ready_for_review(snapshot_id, user_id)

# Lock snapshot
state_machine.lock_snapshot(snapshot_id, user_id, lock_type="Meeting")

# Get status
status = state_machine.get_snapshot_status(snapshot_id)
```

## Benefits

1. **Enforced Workflow**: Cannot skip steps in meeting mode
2. **Gate Protection**: Prevents locking snapshots with data quality issues
3. **Full Audit Trail**: All state transitions and approvals tracked
4. **First-Class Objects**: Exceptions, scenarios, and actions are proper database entities
5. **Meeting Mode**: Structured workflow for weekly meetings

## Future Enhancements

1. Email notifications for exceptions and actions
2. SLA tracking for exception resolution
3. Scenario comparison UI
4. Action impact tracking and reporting
5. Custom gate definitions per entity


