import React, {Component} from 'react';
import ReactDOM from 'react-dom';
import {Query, Builder, BasicConfig, Utils as QbUtils} from 'react-awesome-query-builder';
// import AntdConfig from 'react-awesome-query-builder/lib/config/antd';
// import 'react-awesome-query-builder/css/antd.less'; // or import "antd/dist/antd.css";
import 'react-awesome-query-builder/css/styles.scss';
import 'react-awesome-query-builder/css/compact_styles.scss'; //optional, for more compact styles
const InitialConfig = BasicConfig; // or AntdConfig

const alertFields = window.alertFields;
const alertJsonLogic = window.alertJsonLogic;

const config = {
  ...InitialConfig,
  fields: alertFields,
};

let tree;
if(alertJsonLogic) {
  tree = QbUtils.loadFromJsonLogic(alertJsonLogic, config)
} else {
  tree = QbUtils.loadTree({"id": "new", "type": "group"})
}

class DemoQueryBuilder extends Component {
    state = {
      tree: QbUtils.checkTree(tree, config),
      config: config
    };
    
    render = () => (
      <div>
        <Query
            {...config} 
            value={this.state.tree}
            onChange={this.onChange}
            renderBuilder={this.renderBuilder}
        />
        {this.renderResult(this.state)}
      </div>
    )

    renderBuilder = (props) => (
      <div className="query-builder-container">
        <label>Alert conditions</label>
        <div className="query-builder qb-lite">
            <Builder {...props} />
        </div>
      </div>
    )

    renderResult = ({tree: immutableTree, config}) => (
      <div className="query-builder-result" style={{display: 'none'}}>
          <div>JsonLogic: <pre>{JSON.stringify(QbUtils.jsonLogicFormat(immutableTree, config))}</pre></div>
      </div>
    )
    
    onChange = (immutableTree, config) => {
      // Tip: for better performance you can apply `throttle` - see `examples/demo`
      this.setState({tree: immutableTree, config: config});

      const jsonlogic_e = document.getElementsByName("jsonlogic_json")[0]
      const jsonlogic = QbUtils.jsonLogicFormat(immutableTree, config);
      if (jsonlogic.logic) {
        jsonlogic_e.value = JSON.stringify(jsonlogic.logic);
      } else {
        jsonlogic_e.value = '';
      }
      console.log("set", jsonlogic_e.value)
    }
}

const rootElement = window.document.getElementById('root');

ReactDOM.render(
  <DemoQueryBuilder />
  , rootElement);
