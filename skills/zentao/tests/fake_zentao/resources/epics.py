from ..route import Route

ROUTES = [
    Route('epic.create', 'POST', '/api.php/v2/epics', 'epic', 'create', required_query=(), required_body=('productID', 'title'), enum_values=(('category', ('experience', 'feature', 'improve', 'interface', 'other', 'performance', 'safe')), ('source', ('bug', 'competitor', 'customer', 'dev', 'forum', 'market', 'operation', 'other', 'partner', 'po', 'service', 'support', 'tester', 'user')))),
    Route('epic.edit', 'PUT', '/api.php/v2/epics/{storyID}', 'epic', 'edit', required_query=(), required_body=('title',), enum_values=()),
    Route('epic.change', 'PUT', '/api.php/v2/epics/{storyID}/change', 'epic', 'change', required_query=(), required_body=('reviewer',), enum_values=()),
    Route('epic.list_product', 'GET', '/api.php/v2/products/{productID}/epics', 'epic', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('allstory', 'assignedtome', 'draftstory', 'openedbyme', 'reviewbyme', 'unclosed')),)),
    Route('epic.view', 'GET', '/api.php/v2/epics/{storyID}', 'epic', 'view', required_query=(), required_body=(), enum_values=()),
    Route('epic.close', 'PUT', '/api.php/v2/epics/{storyID}/close', 'epic', 'close', required_query=(), required_body=('closedReason',), enum_values=(('closedReason', ('bydesign', 'cancel', 'done', 'duplicate', 'postponed', 'subdivided', 'willnotdo')),)),
    Route('epic.activate', 'PUT', '/api.php/v2/epics/{storyID}/activate', 'epic', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('epic.delete', 'DELETE', '/api.php/v2/epics/{storyID}', 'epic', 'delete', required_query=(), required_body=(), enum_values=()),
]
