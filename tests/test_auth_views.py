
def test_profile_view_renders_form(authenticated_client):
    response = authenticated_client.get('/auth/profile')
    assert response.status_code == 200

    html = response.data.decode('utf-8')
    assert 'name="first_name"' in html
    assert 'name="last_name"' in html
    assert 'type="submit"' in html


def test_change_password_view_renders_form(authenticated_client):
    response = authenticated_client.get('/auth/change-password')
    assert response.status_code == 200

    html = response.data.decode('utf-8')
    assert 'name="current_password"' in html
    assert 'name="new_password"' in html
    assert 'name="new_password2"' in html
    assert 'type="submit"' in html
