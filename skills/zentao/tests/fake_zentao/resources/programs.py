from ..route import Route

ROUTES = [
    Route('program.create', 'POST', '/api.php/v2/programs', 'program', 'create', required_query=(), required_body=('name', 'begin', 'end'), enum_values=()),
    Route('program.edit', 'PUT', '/api.php/v2/programs/{programID}', 'program', 'edit', required_query=(), required_body=('name', 'begin', 'end'), enum_values=()),
    Route('program.list', 'GET', '/api.php/v2/programs', 'program', 'list', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'closed', 'delayed', 'doing', 'suspended', 'unclosed', 'wait')),)),
    Route('program.view', 'GET', '/api.php/v2/programs/{programID}', 'program', 'view', required_query=(), required_body=(), enum_values=()),
    Route('program.delete', 'DELETE', '/api.php/v2/programs/{programID}', 'program', 'delete', required_query=(), required_body=(), enum_values=()),
]
