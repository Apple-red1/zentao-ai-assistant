from ..route import Route

ROUTES = [
    Route('story.create', 'POST', '/api.php/v2/stories', 'story', 'create', required_query=(), required_body=('productID', 'title'), enum_values=(('category', ('experience', 'feature', 'improve', 'interface', 'other', 'performance', 'safe')), ('source', ('bug', 'competitor', 'customer', 'dev', 'forum', 'market', 'operation', 'other', 'partner', 'po', 'service', 'support', 'tester', 'user')))),
    Route('story.edit', 'PUT', '/api.php/v2/stories/{storyID}', 'story', 'edit', required_query=(), required_body=('title',), enum_values=()),
    Route('story.change', 'PUT', '/api.php/v2/stories/{storyID}/change', 'story', 'change', required_query=(), required_body=('reviewer',), enum_values=()),
    Route('story.list_product', 'GET', '/api.php/v2/products/{productID}/stories', 'story', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('allstory', 'assignedtome', 'draftstory', 'openedbyme', 'reviewbyme')),)),
    Route('story.list_project', 'GET', '/api.php/v2/projects/{projectID}/stories', 'story', 'list_project', required_query=(), required_body=(), enum_values=(('browseType', ('allstory', 'assignedtome', 'draftstory', 'openedbyme', 'reviewbyme')),)),
    Route('story.list_execution', 'GET', '/api.php/v2/executions/{executionID}/stories', 'story', 'list_execution', required_query=(), required_body=(), enum_values=(('browseType', ('allstory',)),)),
    Route('story.view', 'GET', '/api.php/v2/stories/{storyID}', 'story', 'view', required_query=(), required_body=(), enum_values=()),
    Route('story.close', 'PUT', '/api.php/v2/stories/{storyID}/close', 'story', 'close', required_query=(), required_body=('closedReason',), enum_values=(('closedReason', ('bydesign', 'cancel', 'done', 'duplicate', 'postponed', 'subdivided', 'willnotdo')),)),
    Route('story.activate', 'PUT', '/api.php/v2/stories/{storyID}/activate', 'story', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('story.delete', 'DELETE', '/api.php/v2/stories/{storyID}', 'story', 'delete', required_query=(), required_body=(), enum_values=()),
]
