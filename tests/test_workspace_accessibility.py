from html.parser import HTMLParser

from fastapi.testclient import TestClient

from app.main import app


class FormMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.label_targets = []
        self.controls = []
        self.current_links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'label' and attrs.get('for'):
            self.label_targets.append(attrs['for'])
        if tag in ('input', 'select', 'textarea') and attrs.get('type') not in ('hidden', 'checkbox'):
            self.controls.append(attrs)
        if tag == 'a' and attrs.get('aria-current') == 'page':
            self.current_links.append(attrs.get('href'))


def test_workspace_form_names_and_navigation(monkeypatch, tmp_path):
    monkeypatch.setenv('CARRIEROS_DB', str(tmp_path / 'accessibility.db'))
    with TestClient(app) as client:
        response = client.post('/signup', data={
            'full_name': 'Local QA', 'company_name': 'Fictional QA Fleet',
            'email': 'accessibility@example.com', 'password': 'LocalFixture!42',
            'plan': 'free_operator', 'accepted_terms': 'on',
        }, follow_redirects=False)
        assert response.status_code == 303
        for route in ('/loads/new', '/rate-quotes/new'):
            response = client.get(route)
            assert response.status_code == 200
            markup = FormMarkup()
            markup.feed(response.text)
            assert markup.controls
            assert len(markup.ids) == len(set(markup.ids))
            for control in markup.controls:
                assert control.get('id') in markup.label_targets, control.get('name')
            assert 'href="#workspace-main"' in response.text
            assert 'id="workspace-main" tabindex="-1"' in response.text
        for route in ('/payments', '/financials'):
            response = client.get(route)
            assert response.status_code == 200
            markup = FormMarkup()
            markup.feed(response.text)
            assert markup.current_links == [route]
