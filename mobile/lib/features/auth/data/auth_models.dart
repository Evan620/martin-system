// lib/features/auth/data/auth_models.dart
enum UserRole { admin, twgFacilitator, twgMember, secretariatLead, unknown }

UserRole _roleFromApi(String raw) => switch (raw) {
      'ADMIN' => UserRole.admin,
      'TWG_FACILITATOR' => UserRole.twgFacilitator,
      'TWG_MEMBER' => UserRole.twgMember,
      'SECRETARIAT_LEAD' => UserRole.secretariatLead,
      _ => UserRole.unknown,
    };

class AuthTokens {
  const AuthTokens({required this.access, required this.refresh});
  final String access;
  final String refresh;

  factory AuthTokens.fromLoginJson(Map<String, dynamic> json) => AuthTokens(
        access: json['access_token'] as String,
        refresh: json['refresh_token'] as String,
      );
}

class Twg {
  const Twg({required this.id, required this.name});
  final String id;
  final String name;
  factory Twg.fromJson(Map<String, dynamic> j) =>
      Twg(id: j['id'].toString(), name: j['name'] as String);
}

class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.role,
    required this.twgs,
  });

  final String id;
  final String email;
  final String fullName;
  final UserRole role;
  final List<Twg> twgs;

  bool get isMember => role == UserRole.twgMember;

  factory AppUser.fromMeJson(Map<String, dynamic> json) => AppUser(
        id: json['id'].toString(),
        email: json['email'] as String,
        fullName: json['full_name'] as String,
        role: _roleFromApi(json['role'] as String),
        twgs: ((json['twgs'] as List?) ?? const [])
            .map((e) => Twg.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
