import type {Metadata} from 'next';
import AgentDashboard from '../../components/AgentDashboard';

export const metadata: Metadata = {
  title: 'Propomi — Panel de agencia',
  description: 'Ofertas, oportunidades y revelado de contacto para agencias inmobiliarias.',
};

export default function AgenciaPage(){
  return <AgentDashboard/>;
}
