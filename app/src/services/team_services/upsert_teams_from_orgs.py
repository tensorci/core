from src import dbi
from src.models import Team, TeamProviderUser
from src.utils.slug import to_slug
from create_team import CreateTeam


class UpsertTeamsFromOrgs(object):

  def __init__(self, provider_user=None):
    self.provider_user = provider_user
    self.provider = self.provider_user.provider

  def perform(self):
    available_repos = self.provider_user.available_repos()

    available_teams_map = {}
    for r in available_repos:
      owner = r.owner
      team_name = owner.login
      team_slug = to_slug(team_name)

      if team_slug not in available_teams_map:
        available_teams_map[team_slug] = {
          'name': team_name,
          'icon': owner.avatar_url
        }

    for slug, info in available_teams_map.iteritems():
      team = dbi.find_one(Team, {'slug': slug})

      if team:
        team = dbi.update(team, {'icon': info['icon']})
      else:
        svc = CreateTeam(name=info['name'], icon=info['icon'], provider=self.provider)
        svc.perform()
        team = svc.team

      dbi.upsert(TeamProviderUser, {
        'team': team,
        'provider_user': self.provider_user
      })