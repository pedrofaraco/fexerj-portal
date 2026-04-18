import { Component } from 'react'
import PropTypes from 'prop-types'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('Portal FEXERJ — erro inesperado:', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="portal-page flex items-center justify-center px-4">
          <div className="surface-card p-8 w-full max-w-sm text-center">
            <h1 className="text-xl font-semibold t-fg mb-2">Algo deu errado</h1>
            <p className="text-sm t-muted mb-6">
              Ocorreu um erro inesperado. Recarregue a página para tentar novamente.
            </p>
            <button
              onClick={() => window.location.reload()}
              className="btn-primary w-full"
            >
              Recarregar
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
}
