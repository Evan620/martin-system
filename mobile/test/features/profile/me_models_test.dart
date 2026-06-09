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
