from ..route import Route

ROUTES = [
    Route('file.upload', 'POST', '/api.php/v2/files', 'file', 'upload', required_query=(), required_body=('file', 'objectType', 'objectID'), enum_values=(('objectType', ('bug', 'story', 'task', 'testcase')),)),
    Route('file.edit', 'PUT', '/api.php/v2/files/{fileID}', 'file', 'edit', required_query=(), required_body=('fileName',), enum_values=()),
    Route('file.delete', 'DELETE', '/api.php/v2/files/{fileID}', 'file', 'delete', required_query=(), required_body=(), enum_values=()),
]
