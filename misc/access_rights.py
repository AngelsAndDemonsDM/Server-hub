class AccessRights:
    BAN_UNBAN = 0b00001
    MODIFY_ACCESS = 0b00010
    ACCESS_OTHER_SERVERS = 0b00100
    VIEW_LOGS = 0b01000
    CREATE_ROLES = 0b10000
    FULL_ACCESS = 0b11111

    def __init__(self, rights: int = 0):
        self.rights = rights

    def has_access(self, access_type: int) -> bool:
        return (self.rights & access_type) == access_type

    def add_access(self, access_type: int):
        if (
            self.has_access(AccessRights.MODIFY_ACCESS)
            or (self.rights & access_type) == access_type
        ):
            self.rights |= access_type

    def remove_access(self, access_type: int):
        if (
            self.has_access(AccessRights.MODIFY_ACCESS)
            or (self.rights & access_type) == access_type
        ):
            self.rights &= ~access_type

    def __int__(self) -> int:
        return self.rights

    @classmethod
    def from_int(cls, rights: int) -> "AccessRights":
        return cls(rights)

    def __str__(self) -> str:
        if self.has_access(AccessRights.FULL_ACCESS):
            return "FULL_ACCESS"

        access_names = []
        if self.has_access(AccessRights.BAN_UNBAN):
            access_names.append("BAN_UNBAN")

        if self.has_access(AccessRights.MODIFY_ACCESS):
            access_names.append("MODIFY_ACCESS")

        if self.has_access(AccessRights.ACCESS_OTHER_SERVERS):
            access_names.append("ACCESS_OTHER_SERVERS")

        if self.has_access(AccessRights.VIEW_LOGS):
            access_names.append("VIEW_LOGS")

        if self.has_access(AccessRights.CREATE_ROLES):
            access_names.append("CREATE_ROLES")

        return " | ".join(access_names) if access_names else "NO_ACCESS"

    def __repr__(self) -> str:
        return f"AccessRights(rights={self.rights})"

    def can_modify(self, other) -> bool:
        return (
            self.has_access(AccessRights.MODIFY_ACCESS)
            and (self.rights & other.rights) == other.rights
        )

    def clear(self):
        self.rights = 0
