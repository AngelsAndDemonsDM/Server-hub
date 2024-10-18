class RoleAlreadyExistsError(Exception):
    pass


class UserAlreadyExistsError(Exception):
    pass


class InsufficientAccessRightsError(Exception):
    pass


class BanError(Exception):
    pass
