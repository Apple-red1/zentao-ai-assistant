from ..route import Route

ROUTES = [
    Route('feedback.create', 'POST', '/api.php/v2/feedbacks', 'feedback', 'create', required_query=(), required_body=('product', 'title'), enum_values=(('type', ('advice', 'bug', 'issue', 'opportunity', 'risk', 'story', 'task', 'todo')),)),
    Route('feedback.edit', 'PUT', '/api.php/v2/feedbacks/{feedbackID}', 'feedback', 'edit', required_query=(), required_body=('product', 'title'), enum_values=(('type', ('advice', 'bug', 'issue', 'opportunity', 'risk', 'story', 'task', 'todo')),)),
    Route('feedback.list_product', 'GET', '/api.php/v2/products/{productID}/feedbacks', 'feedback', 'list_product', required_query=(), required_body=(), enum_values=(('browseType', ('all', 'assigntome', 'doing', 'openedbyme', 'review', 'toclosed', 'wait')),)),
    Route('feedback.view', 'GET', '/api.php/v2/feedbacks/{feedbackID}', 'feedback', 'view', required_query=(), required_body=(), enum_values=()),
    Route('feedback.close', 'PUT', '/api.php/v2/feedbacks/{feedbackID}/close', 'feedback', 'close', required_query=(), required_body=('closedReason',), enum_values=(('closedReason', ('commented', 'refuse', 'repeat')),)),
    Route('feedback.activate', 'PUT', '/api.php/v2/feedbacks/{feedbackID}/activate', 'feedback', 'activate', required_query=(), required_body=(), enum_values=()),
    Route('feedback.delete', 'DELETE', '/api.php/v2/feedbacks/{feedbackID}', 'feedback', 'delete', required_query=(), required_body=(), enum_values=()),
]
