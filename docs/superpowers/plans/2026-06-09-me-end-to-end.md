# Me (Member App) End-to-End — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Checkbox steps. *(Executed via a dynamic Workflow.)*

**Goal:** Wire the Me screen to live data — profile (session), my action items (list + mark done), personal reminders (list/add/delete, new backend routes), device-local notification toggles.

**Architecture:** Backend adds member `/reminders` CRUD (mirrors the meetings `my-rsvp` member pattern). Flutter mirrors the meetings feature: `me_models` + `me_repository` (action items via existing routes; reminders via the new routes) + `me_controller` (sealed state, optimistic mark-done) + a local `NotificationPrefs` (shared_preferences); rewire the seed `me_screen.dart`.

**Tech Stack:** Backend — FastAPI, SQLAlchemy async, pytest. App — flutter_riverpod, dio, intl, shared_preferences, mocktail.

**Spec:** `docs/superpowers/specs/2026-06-09-me-end-to-end-design.md`

**Environment:** Backend from `/Users/evan/ravishing-presence/backend` with `.venv/bin/python -m pytest` (live Postgres via .env). Flutter from `mobile/` (`export PATH="$PATH:/opt/homebrew/bin"`), package `member_app`. Commit per task; never push. Sequential.

**Verified backend:**
- `GET /api/v1/action-items/?mine_only=true&status=` → `List[ActionItemRead]` (`id, description, status[PENDING|IN_PROGRESS|COMPLETED|OVERDUE], due_date, priority, ...`); `PATCH /api/v1/action-items/{id}` with `{status}` — member can update own (owner check), COMPLETED sets completed_at. **Exists.**
- `Reminder` model (`app/models/models.py:237`): `id, user_id, message(<=500), remind_at, meeting_id?, is_sent, created_at`. **No routes yet.**
- `/auth/me` gives profile (have `AppUser`).
- Member route pattern to mirror: `meetings.py:1962 my-rsvp` (auth `get_current_active_user`, scope by `current_user.id`).

---

## Part A — Backend: `/reminders` routes

### Task B1: Reminder schemas + router + tests

**Files:**
- Modify: `backend/app/schemas/schemas.py` (add reminder schemas)
- Create: `backend/app/api/routes/reminders.py`
- Modify: wherever routers are included (find with `grep -rn "include_router" backend/app/main.py backend/app/api`) — register the reminders router under the `/api/v1` prefix, next to meetings/action_items.
- Test: `backend/tests/test_reminders_routes.py`

- [ ] **Step 1: Write the failing test**
```python
# backend/tests/test_reminders_routes.py
"""Member reminders CRUD — scoped to the caller."""
import uuid
from datetime import datetime, timedelta
import pytest


@pytest.mark.asyncio
async def test_create_list_delete_reminder(client, test_user, normal_user_token_headers):
    when = (datetime.utcnow() + timedelta(days=1)).isoformat()
    # create
    r = await client.post("/api/v1/reminders/", headers=normal_user_token_headers,
                          json={"message": "Prep budget notes", "remind_at": when})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["message"] == "Prep budget notes"

    # list — includes it
    r2 = await client.get("/api/v1/reminders/", headers=normal_user_token_headers)
    assert r2.status_code == 200
    assert any(x["id"] == rid for x in r2.json())

    # delete
    r3 = await client.delete(f"/api/v1/reminders/{rid}", headers=normal_user_token_headers)
    assert r3.status_code == 204
    r4 = await client.get("/api/v1/reminders/", headers=normal_user_token_headers)
    assert all(x["id"] != rid for x in r4.json())


@pytest.mark.asyncio
async def test_delete_others_reminder_404(client, db_session, test_user, normal_user_token_headers):
    from app.models.models import Reminder, User, UserRole
    other = User(id=uuid.uuid4(), full_name="Other", email=f"o-{uuid.uuid4()}@x.org",
                 hashed_password="x", role=UserRole.TWG_MEMBER, is_active=True)
    rem = Reminder(id=uuid.uuid4(), user_id=other.id, message="theirs",
                   remind_at=datetime.utcnow() + timedelta(days=1))
    db_session.add_all([other, rem])
    await db_session.commit()
    r = await client.delete(f"/api/v1/reminders/{rem.id}", headers=normal_user_token_headers)
    assert r.status_code == 404
```
- [ ] **Step 2: Run — FAIL** (`cd backend && .venv/bin/python -m pytest tests/test_reminders_routes.py -v`) — 404/no route.

- [ ] **Step 3: Add schemas** in `schemas.py` (near other Read/Create schemas):
```python
class ReminderBase(SchemaBase):
    message: str
    remind_at: datetime
    meeting_id: Optional[uuid.UUID] = None

class ReminderCreate(ReminderBase):
    pass

class ReminderRead(ReminderBase):
    id: uuid.UUID
    user_id: uuid.UUID
    is_sent: bool = False
    created_at: Optional[datetime] = None
```
(`SchemaBase`, `Optional`, `datetime`, `uuid` are already imported in schemas.py.)

- [ ] **Step 4: Create the router**
```python
# backend/app/api/routes/reminders.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.models.models import User, Reminder
from app.schemas.schemas import ReminderCreate, ReminderRead

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/", response_model=List[ReminderRead])
async def list_my_reminders(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.user_id == current_user.id).order_by(Reminder.remind_at)
    )
    return result.scalars().all()


@router.post("/", response_model=ReminderRead, status_code=201)
async def create_my_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    reminder = Reminder(
        user_id=current_user.id,
        message=body.message,
        remind_at=body.remind_at,
        meeting_id=body.meeting_id,
        is_sent=False,
    )
    db.add(reminder)
    await db.commit()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=204)
async def delete_my_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == current_user.id)
    )
    reminder = result.scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=404, detail="Reminder not found")
    await db.delete(reminder)
    await db.commit()
```

- [ ] **Step 5: Register the router.** Find the include pattern (`grep -rn "include_router\|from app.api.routes import" backend/app/main.py`) and add, mirroring action_items:
```python
from app.api.routes import reminders
app.include_router(reminders.router, prefix="/api/v1")   # match the existing prefix style
```
(Use the exact same prefix/style the neighbouring routers use — some include `prefix="/api/v1"` at include time, others set it on an aggregator. Match what `action_items`/`meetings` do.)

- [ ] **Step 6: Run — PASS** (`cd backend && .venv/bin/python -m pytest tests/test_reminders_routes.py -v`).
- [ ] **Step 7: Commit** `git add backend/app/schemas/schemas.py backend/app/api/routes/reminders.py backend/app/main.py backend/tests/test_reminders_routes.py && git commit -m "feat(member): member reminders CRUD routes"`

---

## Part B — Flutter

### Task F1: Dependency
- [ ] Add `shared_preferences: ^2.3.3` to `mobile/pubspec.yaml` deps; `cd mobile && flutter pub get`; commit `chore(mobile): add shared_preferences for notification prefs`.

### Task F2: Models
**Files:** Create `mobile/lib/features/profile/data/me_models.dart`; Test `mobile/test/features/profile/me_models_test.dart`
- [ ] **Step 1: Failing test**
```dart
// test/features/profile/me_models_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:member_app/features/profile/data/me_models.dart';

void main() {
  test('ActionItem.fromJson parses status + done', () {
    final a = ActionItem.fromJson({'id':'a1','description':'Send notes','status':'PENDING','due_date':'2026-06-10T00:00:00Z'});
    expect(a.description, 'Send notes');
    expect(a.status, ActionStatus.pending);
    expect(a.isDone, isFalse);
    expect(ActionItem.fromJson({'id':'a2','description':'x','status':'COMPLETED'}).isDone, isTrue);
  });
  test('Reminder.fromJson parses', () {
    final r = Reminder.fromJson({'id':'r1','message':'Prep','remind_at':'2026-06-10T09:00:00Z','user_id':'u1'});
    expect(r.message, 'Prep');
    expect(r.remindAt.isUtc, isFalse); // local
  });
}
```
- [ ] **Step 2: FAIL.** **Step 3: Implement**
```dart
// lib/features/profile/data/me_models.dart
enum ActionStatus { pending, inProgress, completed, overdue }

ActionStatus _statusFromApi(String? r) => switch (r) {
      'IN_PROGRESS' => ActionStatus.inProgress,
      'COMPLETED' => ActionStatus.completed,
      'OVERDUE' => ActionStatus.overdue,
      _ => ActionStatus.pending,
    };

class ActionItem {
  const ActionItem({required this.id, required this.description, required this.status, required this.dueDate});
  final String id;
  final String description;
  final ActionStatus status;
  final DateTime? dueDate;
  bool get isDone => status == ActionStatus.completed;
  factory ActionItem.fromJson(Map<String, dynamic> j) => ActionItem(
        id: j['id'].toString(),
        description: (j['description'] ?? '').toString(),
        status: _statusFromApi(j['status'] as String?),
        dueDate: j['due_date'] != null ? DateTime.tryParse(j['due_date'].toString())?.toLocal() : null,
      );
}

class Reminder {
  const Reminder({required this.id, required this.message, required this.remindAt});
  final String id;
  final String message;
  final DateTime remindAt;
  factory Reminder.fromJson(Map<String, dynamic> j) => Reminder(
        id: j['id'].toString(),
        message: (j['message'] ?? '').toString(),
        remindAt: DateTime.parse(j['remind_at'].toString()).toLocal(),
      );
}
```
- [ ] **Step 4: PASS. Step 5: Commit** `feat(mobile): me models (action items + reminders)`.

### Task F3: Repository
**Files:** Create `mobile/lib/features/profile/data/me_repository.dart`; Test `mobile/test/features/profile/me_repository_test.dart`
- [ ] **Step 1: Failing test** (mocked Dio; mirror meetings_repository_test)
```dart
// test/features/profile/me_repository_test.dart
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';

class _MockDio extends Mock implements Dio {}
void main() {
  late _MockDio dio; late MeRepository repo;
  setUp(() { dio = _MockDio(); repo = MeRepository(dio: dio); });
  Response<T> resp<T>(T data, {int code = 200}) => Response<T>(data: data, statusCode: code, requestOptions: RequestOptions(path: '/'));

  test('listActionItems hits mine_only', () async {
    when(() => dio.get('/action-items/', queryParameters: any(named: 'queryParameters')))
      .thenAnswer((_) async => resp<List<dynamic>>([{'id':'a1','description':'x','status':'PENDING'}]));
    final items = await repo.listActionItems();
    expect(items.single.description, 'x');
    verify(() => dio.get('/action-items/', queryParameters: {'mine_only': true})).called(1);
  });
  test('markDone PATCHes COMPLETED', () async {
    when(() => dio.patch('/action-items/a1', data: any(named: 'data')))
      .thenAnswer((_) async => resp<Map<String,dynamic>>({'id':'a1','description':'x','status':'COMPLETED'}));
    await repo.markDone('a1');
    verify(() => dio.patch('/action-items/a1', data: {'status': 'COMPLETED'})).called(1);
  });
  test('addReminder POSTs message + remind_at (utc)', () async {
    when(() => dio.post('/reminders/', data: any(named: 'data')))
      .thenAnswer((_) async => resp<Map<String,dynamic>>({'id':'r1','message':'Prep','remind_at':'2026-06-10T09:00:00Z','user_id':'u1'}));
    final r = await repo.addReminder('Prep', DateTime.utc(2026,6,10,9));
    expect(r.message, 'Prep');
  });
}
```
- [ ] **Step 2: FAIL. Step 3: Implement**
```dart
// lib/features/profile/data/me_repository.dart
import 'package:dio/dio.dart';
import 'me_models.dart';

class MeException implements Exception {
  MeException(this.message);
  final String message;
  @override
  String toString() => message;
}

class MeRepository {
  MeRepository({required Dio dio}) : _dio = dio;
  final Dio _dio;

  Future<List<ActionItem>> listActionItems() async {
    try {
      final res = await _dio.get('/action-items/', queryParameters: {'mine_only': true});
      return (res.data as List).cast<Map<String, dynamic>>().map(ActionItem.fromJson).toList();
    } on DioException {
      throw MeException('Could not load your tasks.');
    }
  }

  Future<void> markDone(String id) async {
    try {
      await _dio.patch('/action-items/$id', data: {'status': 'COMPLETED'});
    } on DioException {
      throw MeException('Could not update the task.');
    }
  }

  Future<List<Reminder>> listReminders() async {
    try {
      final res = await _dio.get('/reminders/');
      return (res.data as List).cast<Map<String, dynamic>>().map(Reminder.fromJson).toList();
    } on DioException {
      throw MeException('Could not load your reminders.');
    }
  }

  Future<Reminder> addReminder(String message, DateTime remindAtUtc) async {
    try {
      final res = await _dio.post('/reminders/', data: {
        'message': message,
        'remind_at': remindAtUtc.toUtc().toIso8601String(),
      });
      return Reminder.fromJson(res.data as Map<String, dynamic>);
    } on DioException {
      throw MeException('Could not save the reminder.');
    }
  }

  Future<void> deleteReminder(String id) async {
    try {
      await _dio.delete('/reminders/$id');
    } on DioException {
      throw MeException('Could not delete the reminder.');
    }
  }
}
```
- [ ] **Step 4: PASS. Step 5: Commit** `feat(mobile): me repository (action items + reminders)`.

### Task F4: Controller + NotificationPrefs
**Files:** Create `mobile/lib/features/profile/application/me_controller.dart`, `mobile/lib/features/profile/data/notification_prefs.dart`; Test `mobile/test/features/profile/me_controller_test.dart`
- [ ] **Step 1: Failing test**
```dart
// test/features/profile/me_controller_test.dart
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:mocktail/mocktail.dart';
import 'package:member_app/features/profile/application/me_controller.dart';
import 'package:member_app/features/profile/data/me_models.dart';
import 'package:member_app/features/profile/data/me_repository.dart';

class _MockRepo extends Mock implements MeRepository {}
ActionItem _ai(String id, String st) => ActionItem.fromJson({'id':id,'description':'t$id','status':st});

void main() {
  test('load -> data; markDone optimistic + rollback on error', () async {
    final repo = _MockRepo();
    when(() => repo.listActionItems()).thenAnswer((_) async => [_ai('1','PENDING')]);
    when(() => repo.listReminders()).thenAnswer((_) async => []);
    final c = ProviderContainer(overrides: [meRepositoryProvider.overrideWithValue(repo)]);
    addTearDown(c.dispose);
    await c.read(meControllerProvider.notifier).load();
    expect(c.read(meControllerProvider), isA<MeData>());

    when(() => repo.markDone('1')).thenThrow(MeException('nope'));
    await expectLater(c.read(meControllerProvider.notifier).markDone('1'), throwsA(isA<MeException>()));
    final st = c.read(meControllerProvider) as MeData;
    expect(st.items.single.isDone, isFalse); // rolled back
  });
}
```
- [ ] **Step 2: FAIL. Step 3: Implement** `notification_prefs.dart` (a `NotificationPrefs` reading/writing 3 bools via `SharedPreferences`, defaults true/true/false, with a `notificationPrefsProvider`) and `me_controller.dart`:
```dart
// lib/features/profile/application/me_controller.dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../auth/application/auth_controller.dart';
import '../data/me_models.dart';
import '../data/me_repository.dart';

sealed class MeState { const MeState(); }
class MeLoading extends MeState { const MeLoading(); }
class MeError extends MeState { const MeError(this.message); final String message; }
class MeData extends MeState {
  const MeData({required this.items, required this.reminders});
  final List<ActionItem> items;
  final List<Reminder> reminders;
  MeData copyWith({List<ActionItem>? items, List<Reminder>? reminders}) =>
      MeData(items: items ?? this.items, reminders: reminders ?? this.reminders);
}

final meRepositoryProvider = Provider<MeRepository>((ref) => MeRepository(dio: ref.watch(dioProvider)));

class MeController extends Notifier<MeState> {
  @override
  MeState build() => const MeLoading();
  MeRepository get _repo => ref.read(meRepositoryProvider);

  Future<void> load() async {
    state = const MeLoading();
    try {
      final items = await _repo.listActionItems();
      final reminders = await _repo.listReminders();
      state = MeData(items: items, reminders: reminders);
    } on MeException catch (e) {
      state = MeError(e.message);
    }
  }

  Future<void> markDone(String id) async {
    final s = state;
    if (s is! MeData) return;
    final prev = s.items;
    state = s.copyWith(items: [
      for (final a in prev)
        if (a.id == id) ActionItem(id: a.id, description: a.description, status: ActionStatus.completed, dueDate: a.dueDate) else a,
    ]);
    try {
      await _repo.markDone(id);
    } on MeException {
      state = (state as MeData).copyWith(items: prev);
      rethrow;
    }
  }

  Future<void> addReminder(String message, DateTime atUtc) async {
    final s = state; if (s is! MeData) return;
    final r = await _repo.addReminder(message, atUtc);
    state = s.copyWith(reminders: [...s.reminders, r]..sort((a, b) => a.remindAt.compareTo(b.remindAt)));
  }

  Future<void> deleteReminder(String id) async {
    final s = state; if (s is! MeData) return;
    await _repo.deleteReminder(id);
    state = s.copyWith(reminders: s.reminders.where((r) => r.id != id).toList());
  }
}

final meControllerProvider = NotifierProvider<MeController, MeState>(MeController.new);
```
- [ ] **Step 4: PASS. Step 5: Commit** `feat(mobile): me controller + notification prefs`.

### Task F5: Wire the Me screen
**Files:** Modify `mobile/lib/features/profile/presentation/me_screen.dart`; Test `mobile/test/features/profile/me_screen_test.dart`
- [ ] Rewrite the seed to a `ConsumerStatefulWidget`: `load()` on init; profile header from `authControllerProvider` (`AppUser` name/role/first TWG; initials from full name); render loading/error(+Retry)/data. Action-item rows reuse the seed's checkbox row — tapping an unchecked one calls `meController.markDone(id)` (SnackBar on `MeException`). Reminders section: list each reminder (message + local `DateFormat` of `remindAt`) with a delete affordance, and an **"+ Add a reminder"** that opens a glass sheet (TextField + `showDatePicker`+`showTimePicker` → combine → `meController.addReminder(msg, dt)`). Notification toggles read/write `notificationPrefsProvider` (local). Sign out → `ref.read(authControllerProvider.notifier).signOut()`. Bottom padding 104.
- [ ] Widget test: with mocked `meRepositoryProvider` (one PENDING item + one reminder) and an authed `authControllerProvider`, the screen shows the item description + the reminder message; tapping the item's checkbox calls `markDone`. (Mirror the meetings_screen test harness.)
- [ ] Run `flutter test test/features/profile/` PASS; `flutter analyze lib/features/profile` clean. Commit `feat(mobile): wire Me screen to live data`.

---

## Final verification
- [ ] Backend: `cd backend && .venv/bin/python -m pytest tests/test_reminders_routes.py -v` → pass.
- [ ] App: `cd mobile && export PATH="$PATH:/opt/homebrew/bin" && flutter analyze && flutter test` → clean + all pass.
- [ ] Device: Me tab → profile + my real action items (tap to complete) + reminders (add/delete) + working local toggles. (Reminders need the backend deployed to prod to persist — same caveat as RSVP.)

## Notes
- Reminders + action-item writes need the backend deployed to prod to work on the phone (action-item *reads* already work against prod; reminders routes are new).
- `remind_at` stored/sent as UTC ISO; displayed local.
