from ..route import Route

ROUTES = [
    Route('requirement.create', 'POST', '/api.php/v2/requirements', 'requirement', 'create', required_query=(), required_body=('productID', 'title'), enum_values=(('category', ('experience', 'feature', 'improve', 'interface', 'other', 'performance', 'safe')), ('source', ('bug', 'competitor', 'customer', 'dev', 'forum', 'market', 'operation', 'other', 'partner', 'po', 'service', 'support', 'tester', 'user')))),
    Route('requirement.edit', 'PUT', '/api.php/v2/requirements/{storyID}', 'requirement', 'edit', required_query=(), required_body=('title',), enum_values=()),
    Route('requirement.change', 'PUT', '/api.php/v2/requirements/{storyID}/change', 'requirement', 'change', required_query=(), required_body=('reviewer',), enum_values=()),
    Route('requirement.list_product', 'GET', '/api.php/v2/products/{productID}/requirements', 'requirement', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('allstory', 'assignedtome', 'draftstory', 'openedbyme', 'reviewbyme', 'unclosed')),)),
    Route('requirement.view', 'GET', '/api.php/v2/requirements/{storyID}', 'requirement', 'view', required_query=(), required_body=(), enum_values=()),
    Route('requirement.close', 'PUT', '/api.php/v2/requirements/{storyID}/close', 'requirement', 'close', required_query=(), required_body=('closedReason',), enum_values=(('closedReason', ('bydesign', 'cancel', 'done', 'duplicate', 'postponed', 'subdivided', 'willnotdo')),)),
    Route('requirement.activate', 'PUT', '/api.php/v2/requirements/{storyID}/activate', 'requirement', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('requirement.delete', 'DELETE', '/api.php/v2/requirements/{storyID}', 'requirement', 'delete', required_query=(), required_body=(), enum_values=()),
]
