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
