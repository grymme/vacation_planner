import React, { useState, useEffect } from 'react';
import { teamsApi, UserResponse } from '../api/vacation';
import './TeamsPage.css';

export default function TeamsPage() {
  const [teams, setTeams] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<any>(null);
  const [members, setMembers] = useState<UserResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchTeams();
  }, []);

  const fetchTeams = async () => {
    try {
      const response = await teamsApi.getManagedTeams();
      setTeams(response.data);
    } catch (error) {
      console.error('Failed to fetch teams:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTeamMembers = async (teamId: string) => {
    try {
      const response = await teamsApi.getTeamMembers(teamId);
      setMembers(response.data);
      setSelectedTeam(teams.find(t => t.id === teamId));
    } catch (error) {
      console.error('Failed to fetch team members:', error);
    }
  };

  if (isLoading) return <div className="loading">Loading...</div>;

  return (
    <div className="page">
      <h1>Team Management</h1>
      
      <div className="teams-layout">
        <div className="teams-list">
          <h3>Your Teams</h3>
          {teams.length === 0 ? (
            <p>No teams assigned.</p>
          ) : (
            <ul>
              {teams.map(team => (
                <li 
                  key={team.id}
                  className={selectedTeam?.id === team.id ? 'active' : ''}
                  onClick={() => fetchTeamMembers(team.id)}
                >
                  {team.name}
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div className="team-members">
          {selectedTeam ? (
            <>
              <h3>Members of {selectedTeam.name}</h3>
              {members.length === 0 ? (
                <p>No members in this team.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Email</th>
                      <th>Role</th>
                    </tr>
                  </thead>
                  <tbody>
                    {members.map(member => (
                      <tr key={member.id}>
                        <td>{member.first_name} {member.last_name}</td>
                        <td>{member.email}</td>
                        <td><span className={`role-badge role-${member.role}`}>{member.role}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </>
          ) : (
            <p className="placeholder">Select a team to view members</p>
          )}
        </div>
      </div>
    </div>
  );
}
